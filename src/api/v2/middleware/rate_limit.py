"""
Middleware para controle de rate limiting usando Redis.
Implementa limites por usuário, IP e endpoint.
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import time
import asyncio
from typing import Optional, Dict
import logging
from src.core.redis import redis_client

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self):
        self.redis = redis_client
        self.max_requests = 500  # Máximo de requisições por segundo global
        self.window = 1  # Janela de tempo em segundos
        
        # Limites específicos por endpoint
        self.endpoint_limits = {
            "/comfy/execute": 50,  # Máximo de 50 execuções por segundo
            "/generate/image": 100,  # Máximo de 100 gerações por segundo
            "/generate/video": 20   # Máximo de 20 gerações por segundo
        }
    
    async def _get_current_count(self, key: str) -> int:
        """Obtém contagem atual de requisições."""
        count = await self.redis.get(key)
        return int(count) if count else 0
    
    async def _increment_count(self, key: str) -> int:
        """Incrementa contador e define TTL."""
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.window)
        results = await pipe.execute()
        return int(results[0])
    
    async def is_rate_limited(
        self,
        endpoint: str,
        user_id: Optional[str] = None,
        ip: Optional[str] = None
    ) -> bool:
        """
        Verifica se a requisição deve ser limitada.
        
        Args:
            endpoint: Endpoint sendo acessado
            user_id: ID do usuário (se autenticado)
            ip: IP do cliente
            
        Returns:
            bool indicando se deve ser limitado
        """
        current_time = int(time.time())
        keys = []
        
        # Chave global
        global_key = f"ratelimit:global:{current_time}"
        keys.append((global_key, self.max_requests))
        
        # Chave do endpoint
        if endpoint in self.endpoint_limits:
            endpoint_key = f"ratelimit:endpoint:{endpoint}:{current_time}"
            keys.append((endpoint_key, self.endpoint_limits[endpoint]))
        
        # Chave do usuário
        if user_id:
            user_key = f"ratelimit:user:{user_id}:{current_time}"
            keys.append((user_key, self.max_requests))
        
        # Chave do IP
        if ip:
            ip_key = f"ratelimit:ip:{ip}:{current_time}"
            keys.append((ip_key, self.max_requests))
        
        # Verificar todos os limites
        for key, limit in keys:
            count = await self._increment_count(key)
            if count > limit:
                logger.warning(f"Rate limit excedido para {key}")
                return True
        
        return False

class RateLimitMiddleware:
    """Middleware para aplicar rate limiting."""
    
    def __init__(self):
        self.limiter = RateLimiter()
    
    async def __call__(self, request: Request, call_next):
        # Extrair informações da requisição
        endpoint = request.url.path
        user_id = request.state.user.id if hasattr(request.state, "user") else None
        ip = request.client.host
        
        # Verificar rate limit
        is_limited = await self.limiter.is_rate_limited(endpoint, user_id, ip)
        
        if is_limited:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Muitas requisições. Tente novamente em alguns segundos.",
                    "type": "rate_limit_exceeded"
                }
            )
        
        # Processar requisição
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Erro no middleware de rate limit: {str(e)}")
            raise

# Instância global do middleware
rate_limit_middleware = RateLimitMiddleware() 