"""
Cliente Redis para cache e gerenciamento de sessões
"""
import aioredis
from src.core.config import settings
from typing import Optional
import logging
import asyncio

logger = logging.getLogger(__name__)

# Conexão global do Redis
redis_pool: Optional[aioredis.Redis] = None

async def init_redis_pool() -> aioredis.Redis:
    """
    Inicializa e retorna uma pool de conexões Redis.
    """
    global redis_pool
    
    if redis_pool is None:
        try:
            redis_pool = await aioredis.from_url(
                str(settings.REDIS_URL),
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_TIMEOUT
            )
            logger.info("✅ Conexão Redis estabelecida com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao conectar ao Redis: {e}")
            raise
        
    return redis_pool

async def get_redis() -> aioredis.Redis:
    """
    Retorna a conexão Redis existente ou cria uma nova.
    """
    global redis_pool
    
    if redis_pool is None:
        redis_pool = await init_redis_pool()
    
    return redis_pool

async def close_redis_pool() -> None:
    """
    Fecha a pool de conexões Redis.
    """
    global redis_pool
    
    if redis_pool is not None:
        await redis_pool.close()
        redis_pool = None
        logger.info("✅ Conexão Redis fechada")

async def retry_redis_operation(operation, max_retries=3):
    """Executa operação Redis com retry"""
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(
                f"Tentativa {attempt + 1} falhou: {e}. "
                "Tentando novamente..."
            )
            await asyncio.sleep(1)