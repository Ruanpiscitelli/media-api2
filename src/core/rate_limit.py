"""
Implementa rate limiting usando Redis para controle de requisições por GPU/hora.
"""

import asyncio
from typing import Optional
from fastapi import Request, HTTPException
from redis.asyncio import Redis
import time
import logging

from src.core.redis_client import get_redis
from src.core.config import settings

logger = logging.getLogger(__name__)

class RateLimitError(Exception):
    """Erro específico de rate limit"""
    pass

class RateLimiter:
    """
    Implementa rate limiting por GPU usando Redis.
    Controla requisições por hora e por minuto (burst).
    """
    
    def __init__(self):
        self.redis: Optional[Redis] = None
        self._incr_script = None
        self.default_rate_limit = getattr(settings, 'RATE_LIMIT_DEFAULT', 100)
        self.default_burst_limit = getattr(settings, 'RATE_LIMIT_BURST', 10)
        self.enabled = getattr(settings, 'RATE_LIMIT_ENABLED', True)
        
    async def init(self):
        """Inicializa conexão com Redis e carrega scripts Lua"""
        try:
            if not self.redis:
                self.redis = await get_redis()
            
            await self.redis.ping()
            
            # Script Lua para incremento com TTL atômico
            self._incr_script = """
                local current = redis.call('INCR', KEYS[1])
                if current == 1 then
                    redis.call('EXPIRE', KEYS[1], ARGV[1])
                end
                return current
            """
            
        except Exception as e:
            logger.error(f"Erro inicializando rate limiter: {e}")
            raise RateLimitError(f"Erro inicializando rate limiter: {e}")

    async def _increment_counter(self, key: str, ttl: int) -> int:
        """Executa script Lua para incremento com TTL atômico"""
        try:
            return await self.redis.eval(
                self._incr_script,
                1,
                key,
                ttl
            )
        except Exception as e:
            logger.error(f"Erro incrementando contador: {e}")
            raise RateLimitError("Erro interno no rate limiting")

    async def _get_gpu_id(self, request: Request) -> str:
        """Obtém GPU ID dos parâmetros da rota"""
        gpu_id = request.path_params.get('gpu_id')
        if not gpu_id:
            logger.error("GPU ID não encontrado nos parâmetros da requisição")
            raise HTTPException(status_code=400, detail="GPU ID obrigatório")
        return gpu_id

    async def __call__(self, request: Request):
        """Dependency do FastAPI que aplica o rate limiting"""
        if await self.is_rate_limited(request):
            raise HTTPException(status_code=429, detail="Limite de requisições excedido")

    async def is_rate_limited(self, request: Request) -> bool:
        """
        Verifica se uma requisição deve ser limitada com base na GPU.
        Retorna True se limitada, False caso contrário.
        """
        if not self.enabled:
            return False

        try:
            await self.init()
            gpu_id = await self._get_gpu_id(request)

            # Obter limites
            hour_limit = await self._get_rate_limit(gpu_id)
            burst_limit = await self._get_burst_limit(gpu_id)

            # Incrementar contadores
            hour_count = await self._increment_counter(
                f"rate_limit:hour:{gpu_id}", 
                3600
            )
            minute_count = await self._increment_counter(
                f"rate_limit:burst:{gpu_id}", 
                60
            )

            # Verificar limites
            if hour_count > hour_limit or minute_count > burst_limit:
                logger.warning(f"Limite excedido para GPU {gpu_id}. "
                               f"Contadores: Hora={hour_count}/{hour_limit}, "
                               f"Burst={minute_count}/{burst_limit}")
                return True
            return False

        except HTTPException:
            raise  # Propaga exceções HTTP
        except Exception as e:
            logger.error(f"Erro no rate limiter: {e}", exc_info=True)
            return False  # Fail open em caso de erro

    async def _get_rate_limit(self, gpu_id: str) -> int:
        """Obtém limite de requisições por hora para a GPU"""
        # Implemente lógica personalizada aqui (ex: buscar de configurações)
        return self.default_rate_limit

    async def _get_burst_limit(self, gpu_id: str) -> int:
        """Obtém limite de burst por minuto para a GPU"""
        return self.default_burst_limit

    async def reset_limits(self, gpu_id: str):
        """Reseta contadores para uma GPU específica"""
        await self.init()
        await self.redis.delete(
            f"rate_limit:hour:{gpu_id}",
            f"rate_limit:burst:{gpu_id}"
        )

# Instância global para uso como dependência
rate_limiter = RateLimiter()