"""
Cliente Redis para gerenciamento de cache e filas
"""
import aioredis
from typing import Optional, Any, Callable
from src.core.config import settings
import logging
import asyncio
from prometheus_client import Counter, Gauge
from functools import wraps
import warnings

logger = logging.getLogger(__name__)

# Métricas Prometheus
REDIS_OPS = Counter('redis_operations_total', 'Total de operações Redis', ['operation'])
REDIS_ERRORS = Counter('redis_errors_total', 'Total de erros Redis', ['type'])
REDIS_CONN_ACTIVE = Gauge('redis_connections_active', 'Conexões Redis ativas')

# Instância global do cliente Redis
redis_client: Optional[aioredis.Redis] = None

def with_redis_retry(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator para retry automático em operações Redis.
    
    Args:
        max_retries: Número máximo de tentativas
        delay: Delay entre tentativas em segundos
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    REDIS_ERRORS.labels(type=type(e).__name__).inc()
                    
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Tentativa {attempt + 1} falhou: {e}. "
                            f"Tentando novamente em {delay}s..."
                        )
                        await asyncio.sleep(delay)
                    
            logger.error(f"Todas as {max_retries} tentativas falharam")
            raise last_error
            
        return wrapper
    return decorator

@with_redis_retry()
async def init_redis_pool() -> aioredis.Redis:
    """
    Inicializa e retorna uma pool de conexões Redis.
    
    Returns:
        aioredis.Redis: Cliente Redis configurado
    
    Raises:
        Exception: Se a conexão falhar após as tentativas
    """
    global redis_client
    
    try:
        redis_client = await aioredis.from_url(
            str(settings.REDIS_URL),  # Usa URL validada do Pydantic
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_timeout=settings.REDIS_TIMEOUT,
            retry_on_timeout=True
        )
        
        # Testa a conexão
        await redis_client.ping()
        REDIS_CONN_ACTIVE.set(1)
        logger.info("✅ Conexão Redis estabelecida com sucesso")
        return redis_client
        
    except Exception as e:
        REDIS_CONN_ACTIVE.set(0)
        logger.error(f"❌ Erro ao conectar ao Redis: {e}")
        raise

async def get_redis() -> aioredis.Redis:
    """
    Retorna uma instância do cliente Redis, criando se necessário.
    
    Returns:
        aioredis.Redis: Cliente Redis configurado
    """
    global redis_client
    
    if redis_client is None:
        redis_client = await init_redis_pool()
    
    return redis_client

async def close_redis_pool() -> None:
    """
    Fecha a pool de conexões Redis.
    """
    global redis_client
    
    if redis_client is not None:
        await redis_client.close()
        redis_client = None
        REDIS_CONN_ACTIVE.set(0)
        logger.info("✅ Conexão Redis fechada")

@with_redis_retry()
async def execute_redis_operation(operation: Callable, *args, **kwargs) -> Any:
    """
    Executa uma operação Redis com retry e métricas.
    
    Args:
        operation: Função Redis a ser executada
        *args: Argumentos posicionais
        **kwargs: Argumentos nomeados
        
    Returns:
        Resultado da operação
    """
    REDIS_OPS.labels(operation=operation.__name__).inc()
    return await operation(*args, **kwargs)

async def check_redis_health() -> bool:
    """
    Verifica a saúde da conexão Redis.
    
    Returns:
        bool: True se saudável, False caso contrário
    """
    try:
        redis = await get_redis()
        await redis.ping()
        return True
    except Exception as e:
        logger.error(f"Verificação de saúde Redis falhou: {e}")
        return False

# Deprecation warning
def create_redis_pool(*args, **kwargs):
    """
    @deprecated: Use init_redis_pool instead
    """
    warnings.warn(
        "create_redis_pool is deprecated, use init_redis_pool instead",
        DeprecationWarning,
        stacklevel=2
    )
    return init_redis_pool(*args, **kwargs)