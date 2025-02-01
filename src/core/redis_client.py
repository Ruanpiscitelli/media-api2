"""
Cliente Redis com pool de conexões
"""
import aioredis
from typing import Optional
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)

redis_pool: Optional[aioredis.Redis] = None

async def create_redis_pool() -> aioredis.Redis:
    """Cria pool de conexões Redis"""
    global redis_pool
    
    if redis_pool is None:
        try:
            redis_pool = await aioredis.create_redis_pool(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                encoding="utf-8",
                maxsize=20,  # Máximo de conexões no pool
                timeout=settings.REDIS_TIMEOUT,
                ssl=settings.REDIS_SSL
            )
            logger.info("Pool Redis criado com sucesso")
        except Exception as e:
            logger.error(f"Erro criando pool Redis: {e}")
            raise
            
    return redis_pool

async def get_redis() -> aioredis.Redis:
    """Obtém conexão do pool"""
    if redis_pool is None:
        await create_redis_pool()
    return redis_pool

async def close_redis_pool():
    """Fecha pool de conexões"""
    global redis_pool
    if redis_pool is not None:
        redis_pool.close()
        await redis_pool.wait_closed()
        redis_pool = None 