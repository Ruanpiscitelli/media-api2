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
from fastapi import FastAPI
from src.core.rate_limit import rate_limiter
import os
import anyio
from src.core.cache_manager import cache_manager

logger = logging.getLogger(__name__)

async def init_redis():
    """Inicializa conexão com Redis"""
    try:
        # Usar o novo sistema de cache
        await cache_manager.ensure_connection()
        logger.info("Redis inicializado com sucesso")
        # Retornar a conexão do cache_manager
        return cache_manager.get_connection()
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

async def initialize_api(app: FastAPI):
    """Inicializa componentes da API"""
    try:
        logger.info("Iniciando inicialização da API...")
        
        # Configurar pool de threads
        limiter = anyio.to_thread.current_default_thread_limiter()
        limiter.total_tokens = settings.MAX_THREADS  # Definido no config.py
        
        # Inicializar Redis primeiro
        redis_pool = await create_redis_pool()
        app.state.redis = redis_pool
        
        # Inicializar rate limiter após Redis
        rate_limiter = RateLimiter()
        await rate_limiter.init()
        
        # Inicializar Fish Speech
        from src.services.speech import speech_service
        await speech_service.initialize()
        
        # Resto das inicializações...
        await init_db()
        setup_monitoring()
        
        logger.info("API inicializada com sucesso")
        
    except Exception as e:
        logger.error(f"Erro na inicialização da API: {e}")
        raise

async def validate_environment():
    """Valida ambiente antes de iniciar"""
    try:
        # Verificar versão do Python
        import sys
        if sys.version_info >= (3, 12):
            raise RuntimeError(
                "Python 3.12 não é suportado pelo PyTorch. "
                "Use Python 3.11 ou anterior."
            )
            
        # Resto das validações...
    except Exception as e:
        raise RuntimeError(f"Erro validando ambiente: {e}")

async def validate_ffmpeg():
    """Valida instalação do FFmpeg"""
    try:
        import ffmpeg
        
        # Verificar se ffmpeg está instalado
        result = await asyncio.create_subprocess_shell(
            "ffmpeg -version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        
        if result.returncode != 0:
            raise RuntimeError("FFmpeg não encontrado no sistema")
            
        # Verificar codecs necessários
        result = await asyncio.create_subprocess_shell(
            "ffmpeg -codecs",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        stdout = stdout.decode()
        
        required_codecs = ['h264', 'hevc', 'aac', 'opus']
        missing_codecs = []
        
        for codec in required_codecs:
            if codec not in stdout:
                missing_codecs.append(codec)
                
        if missing_codecs:
            raise RuntimeError(
                f"Codecs necessários não encontrados: {', '.join(missing_codecs)}"
            )
            
    except ImportError:
        raise RuntimeError("Módulo python-ffmpeg não instalado")
    except Exception as e:
        raise RuntimeError(f"Erro validando FFmpeg: {e}") 