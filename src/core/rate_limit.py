"""
Rate limiting simples
"""
import logging
from fastapi import Request, HTTPException
from src.core.cache import cache

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Implementa rate limiting por GPU usando Redis.
    Controla requisições por hora e por minuto (burst).
    """
    
    def __init__(self):
        self.cache = cache
        
    async def is_rate_limited(self, request: Request):
        """Verifica se requisição excedeu limite"""
        # ... implementação ...

rate_limiter = RateLimiter()