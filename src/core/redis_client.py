"""
Cliente Redis com pool de conexões
"""
from redis.asyncio import Redis, ConnectionPool
from typing import Optional
from src.core.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

redis_pool: Optional[ConnectionPool] = None
redis_client: Optional[Redis] = None

async def create_redis_pool() -> Redis:
    """Cria pool de conexões Redis"""
    global redis_pool, redis_client
    
    if redis_pool is None:
        try:
            redis_pool = ConnectionPool(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                ssl=settings.redis_ssl,
                decode_responses=True,
                max_connections=20,
                socket_timeout=settings.redis_timeout
            )
            
            redis_client = Redis(connection_pool=redis_pool)
            logger.info("Pool Redis criado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro criando pool Redis: {e}")
            raise
            
    return redis_client

async def get_redis_client(max_retries: int = 3) -> Redis:
    """
    Obtém cliente Redis do pool de conexões com retry
    """
    global redis_client
    
    for attempt in range(max_retries):
        try:
            if redis_client is None:
                await create_redis_pool()
                
            # Verifica se a conexão ainda está ativa
            await redis_client.ping()
            return redis_client
            
        except Exception as e:
            logger.warning(f"Tentativa {attempt + 1} de conectar ao Redis falhou: {e}")
            
            # Reseta o cliente para forçar nova conexão na próxima tentativa
            redis_client = None
            
            if attempt == max_retries - 1:
                logger.error("Todas as tentativas de conexão Redis falharam")
                raise
                
            await asyncio.sleep(1)

async def get_redis() -> Redis:
    """Alias para get_redis_client para manter compatibilidade"""
    return await get_redis_client()

async def close_redis_pool():
    """Fecha pool de conexões"""
    global redis_pool, redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None
    if redis_pool is not None:
        await redis_pool.disconnect()
        redis_pool = None

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