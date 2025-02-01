"""Cache simples com Redis"""
import logging
import aioredis
from src.core.config import settings

logger = logging.getLogger(__name__)

class Cache:
    def __init__(self):
        self.redis = None
        
    async def connect(self):
        """Conecta ao Redis"""
        try:
            self.redis = await aioredis.from_url(settings.REDIS_URL)
            await self.redis.ping()
            logger.info("✅ Redis OK")
        except Exception as e:
            logger.error(f"❌ Redis erro: {e}")
            
    async def get(self, key: str):
        """Obtém valor"""
        if self.redis:
            return await self.redis.get(key)
        return None

    async def set(self, key: str, value: str, expire: int = 3600):
        """Define valor"""
        if self.redis:
            await self.redis.set(key, value, ex=expire)

cache = Cache() 