"""
Middleware de rate limiting
"""
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException, FastAPI
import logging
import time
from typing import Optional
from src.core.initialization import cache_manager
from src.core.config import settings

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.cache = None
        self.requests = {}
        
    async def initialize(self):
        if self.cache is None:
            self.cache = await cache_manager.get_cache('rate_limit')
            
    async def dispatch(self, request: Request, call_next):
        await self.initialize()
        try:
            # Verificar se rate limiting está ativo
            if not settings.RATE_LIMIT_ENABLED:
                return await call_next(request)
                
            # Tentar rate limiting com Redis
            try:
                await self._check_redis_rate_limit(request)
            except Exception as redis_error:
                logger.error(f"Erro no Redis rate limit: {redis_error}")
                # Fallback para rate limiting em memória
                if self._check_memory_rate_limit(request):
                    raise HTTPException(
                        status_code=429,
                        detail="Too Many Requests"
                    )
                    
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"Erro no middleware de rate limit: {e}")
            # Em caso de erro no middleware, permitir requisição
            return await call_next(request)
            
    def _check_memory_rate_limit(self, request: Request) -> bool:
        """Rate limiting em memória como fallback"""
        key = self._get_rate_limit_key(request)
        now = time.time()
        
        # Limpar requisições antigas
        self.requests = {
            k: v for k, v in self.requests.items()
            if now - v[-1] < settings.RATE_LIMIT_WINDOW
        }
        
        # Verificar limite
        if key in self.requests:
            if len(self.requests[key]) >= settings.RATE_LIMIT_MAX:
                return True
            self.requests[key].append(now)
        else:
            self.requests[key] = [now]
            
        return False 

    def _get_rate_limit_key(self, request: Request) -> str:
        """Gera chave única para rate limiting"""
        client_ip = request.client.host
        route = request.url.path
        return f"rate_limit:{client_ip}:{route}"

    async def _check_redis_rate_limit(self, request: Request):
        """Implementa rate limiting usando Redis"""
        key = self._get_rate_limit_key(request)
        # ... implementação do rate limiting com Redis ... 