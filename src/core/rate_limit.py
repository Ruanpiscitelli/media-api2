"""
Implementa rate limiting usando Redis para controle de requisições por GPU/hora.
"""

import asyncio
from typing import Optional
from fastapi import Request, HTTPException
from redis.asyncio import Redis
import time
import logging

from src.core.redis_client import get_redis_client
from src.core.config import settings

logger = logging.getLogger(__name__)

class RateLimitError(Exception):
    """Erro específico de rate limit"""
    pass

class RateLimiter:
    """
    Implementa rate limiting por usuário/GPU usando Redis.
    Controla requisições por hora e por minuto.
    """
    
    def __init__(self):
        """Inicializa o rate limiter"""
        self.redis: Optional[Redis] = None
        self._lock = asyncio.Lock()
        # Valores default caso não existam nas configurações
        self.default_rate_limit = getattr(settings, 'RATE_LIMIT_DEFAULT', 100)
        self.default_burst_limit = getattr(settings, 'RATE_LIMIT_BURST', 10)
        
    async def init(self):
        """Inicializa conexão com Redis"""
        try:
            # Inicializa conexão Redis se ainda não existir
            if not self.redis:
                self.redis = await get_redis_client()
                
            # Verificar se Redis está respondendo
            await self.redis.ping()
            
            # Limpar contadores antigos
            await self.redis.delete("rate_limit:*")
            
        except Exception as e:
            logger.error(f"Erro inicializando rate limiter: {e}")
            raise RateLimitError(f"Erro inicializando rate limiter: {e}")
            
    async def _get_rate_limit(self, user_id: str) -> int:
        """Obtém limite de requisições para um usuário"""
        return self.default_rate_limit
        
    async def _get_burst_limit(self, user_id: str) -> int:
        """Obtém limite de burst para um usuário"""
        return self.default_burst_limit
        
    async def __call__(self, request: Request) -> bool:
        """
        Permite usar o rate_limiter como dependência do FastAPI
        """
        return await self.is_rate_limited(request)
        
    async def is_rate_limited(self, request: Request) -> bool:
        """
        Verifica se uma requisição deve ser limitada.
        """
        await self.init()
        
        # Obtém identificador do usuário
        user_id = getattr(request.state, "user_id", request.client.host)
        
        # Chaves Redis para contadores
        hour_key = f"rate_limit:hour:{user_id}"
        minute_key = f"rate_limit:minute:{user_id}"
        
        # Obtém limites
        hour_limit = await self._get_rate_limit(user_id)
        burst_limit = await self._get_burst_limit(user_id)
        
        # Incrementa contadores
        pipe = self.redis.pipeline()
        now = int(time.time())
        
        # Contador por hora
        pipe.incr(hour_key)
        pipe.expire(hour_key, 3600)  # expira em 1h
        
        # Contador por minuto
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)  # expira em 1min
        
        hour_count, _, minute_count, _ = await pipe.execute()
        
        # Verifica limites
        if hour_count > hour_limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit excedido",
                    "limit": hour_limit,
                    "reset": 3600 - (now % 3600)
                }
            )
            
        if minute_count > burst_limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Burst limit excedido",
                    "limit": burst_limit,
                    "reset": 60 - (now % 60)
                }
            )
            
        return False
        
    async def reset_limits(self, user_id: str):
        """Reseta contadores de limite para um usuário"""
        await self.init()
        pipe = self.redis.pipeline()
        pipe.delete(f"rate_limit:hour:{user_id}")
        pipe.delete(f"rate_limit:minute:{user_id}")
        await pipe.execute()

# Instância global para uso como dependência
rate_limiter = RateLimiter()