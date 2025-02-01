"""
Funções de inicialização da API
"""
import asyncio
import logging
from pathlib import Path
from src.core.config import settings
from src.core.db.init_db import init_db
from src.core.redis_client import create_redis_pool
from src.core.monitoring import setup_monitoring

logger = logging.getLogger(__name__)

async def init_redis():
    """Inicializa conexão com Redis"""
    try:
        redis = await create_redis_pool()
        await redis.ping()
        logger.info("Redis inicializado com sucesso")
        return redis
    except Exception as e:
        logger.error(f"Erro inicializando Redis: {e}")
        raise

async def init_directories():
    """Cria diretórios necessários"""
    try:
        directories = [
            settings.TEMP_DIR,
            settings.SUNO_OUTPUT_DIR,
            settings.SUNO_CACHE_DIR,
            settings.SHORTS_OUTPUT_DIR,
            Path("/workspace/logs"),
            Path("/workspace/media"),
            Path("/workspace/cache"),
            Path("/workspace/models"),
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Diretório criado: {directory}")
            
    except Exception as e:
        logger.error(f"Erro criando diretórios: {e}")
        raise

async def init_monitoring():
    """Inicializa sistema de monitoramento"""
    try:
        setup_monitoring()
        logger.info("Monitoramento inicializado")
    except Exception as e:
        logger.error(f"Erro inicializando monitoramento: {e}")
        raise

async def initialize_api():
    """Inicializa todos os componentes da API"""
    try:
        # Inicializar componentes em paralelo
        await asyncio.gather(
            init_redis(),
            init_db(),
            init_directories(),
            init_monitoring()
        )
        logger.info("API inicializada com sucesso")
    except Exception as e:
        logger.error(f"Erro fatal inicializando API: {e}")
        raise 