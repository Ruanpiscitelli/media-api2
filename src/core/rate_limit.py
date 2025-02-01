"""
Rate limiting com suporte a Redis
"""
import logging
from fastapi import Request, HTTPException
from datetime import datetime, timedelta
from typing import Dict, Tuple
import asyncio
from src.core.redis_client import redis_pool

logger = logging.getLogger(__name__)

# Constantes de configuração
MAX_REQUESTS_PER_HOUR = 1000
WINDOW_HOURS = 1
RATE_LIMIT_ERROR_MSG = "Too many requests. Please try again later."
INTERNAL_ERROR_MSG = "Rate limiting temporarily unavailable. Request denied for security."

class RateLimiter:
    """Limitador de taxa de requisições com Redis"""
    
    def __init__(self):
        self.requests: Dict[str, Tuple[int, datetime]] = {}
        self.lock = asyncio.Lock()
        
    async def __call__(self, request: Request):
        """Rate limiting por IP com fail-closed em caso de erro"""
        try:
            client_ip = request.client.host
            now = datetime.now()
            
            # Tentar usar Redis primeiro
            if redis_pool:
                try:
                    key = f"rate_limit:{client_ip}"
                    count = await redis_pool.incr(key)
                    if count == 1:
                        await redis_pool.expire(key, WINDOW_HOURS * 3600)
                    if count > MAX_REQUESTS_PER_HOUR:
                        logger.warning(f"Rate limit excedido para IP {client_ip}")
                        raise HTTPException(
                            status_code=429,
                            detail=RATE_LIMIT_ERROR_MSG
                        )
                    return True
                except Exception as e:
                    logger.error(f"Erro no Redis rate limit: {e}")
                    # Fallback para memória local em caso de erro do Redis
            
            # Implementação em memória local
            async with self.lock:
                if client_ip in self.requests:
                    count, start_time = self.requests[client_ip]
                    if now - start_time > timedelta(hours=WINDOW_HOURS):
                        self.requests[client_ip] = (1, now)
                    elif count >= MAX_REQUESTS_PER_HOUR:
                        logger.warning(f"Rate limit excedido para IP {client_ip}")
                        raise HTTPException(
                            status_code=429,
                            detail=RATE_LIMIT_ERROR_MSG
                        )
                    else:
                        self.requests[client_ip] = (count + 1, start_time)
                else:
                    self.requests[client_ip] = (1, now)
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro crítico no rate limit: {e}")
            # Fail closed - nega acesso em caso de erro
            raise HTTPException(
                status_code=503,
                detail=INTERNAL_ERROR_MSG
            )
            
        return True

# Instância global
rate_limiter = RateLimiter()