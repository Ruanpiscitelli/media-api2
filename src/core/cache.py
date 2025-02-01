"""
Cache distribuído com Redis
"""
from typing import Any, Optional
import pickle
from redis.asyncio import Redis
from src.core.config import settings

class RedisCache:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.default_ttl = 3600  # 1 hora

    async def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache"""
        data = await self.redis.get(f"cache:{key}")
        if data:
            return pickle.loads(data)
        return None

    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ):
        """Define valor no cache"""
        data = pickle.dumps(value)
        await self.redis.set(
            f"cache:{key}",
            data,
            ex=ttl or self.default_ttl
        )

    async def delete(self, key: str):
        """Remove valor do cache"""
        await self.redis.delete(f"cache:{key}")

# Usar como decorator
from functools import wraps

def cached(ttl: Optional[int] = None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            cached_value = await cache.get(cache_key)
            
            if cached_value is not None:
                return cached_value
                
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator