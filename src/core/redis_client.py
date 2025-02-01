"""
Cliente Redis para gerenciamento de cache e filas
"""
import aioredis
from typing import Optional
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)

async def create_redis_pool() -> Optional[aioredis.Redis]:
    """
    Cria e retorna uma pool de conexões Redis.
    
    Returns:
        aioredis.Redis: Cliente Redis configurado
        None: Se a conexão falhar
    """
    try:
        # Cria pool de conexões Redis usando as configurações do settings
        redis = await aioredis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            password=settings.REDIS_PASSWORD,
            encoding="utf-8",
            decode_responses=True,
            max_connections=10
        )
        
        # Testa a conexão
        await redis.ping()
        logger.info("Conexão Redis estabelecida com sucesso")
        return redis
        
    except Exception as e:
        logger.error(f"Erro ao conectar ao Redis: {e}")
        return None

# Instância global do cliente Redis
redis_client: Optional[aioredis.Redis] = None

async def get_redis() -> Optional[aioredis.Redis]:
    """
    Retorna uma instância do cliente Redis, criando se necessário.
    
    Returns:
        aioredis.Redis: Cliente Redis configurado
        None: Se a conexão falhar
    """
    global redis_client
    
    if redis_client is None:
        redis_client = await create_redis_pool()
    
    return redis_client