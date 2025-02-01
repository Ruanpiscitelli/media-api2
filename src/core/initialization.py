"""
Funções de inicialização da API
"""
import asyncio
import logging
from pathlib import Path
from src.core.config import settings
from src.core.db.init_db import init_db
from src.core.redis_client import init_redis_pool
from src.core.monitoring import setup_monitoring
from fastapi import FastAPI
from src.core.rate_limit import rate_limiter
import os
import anyio
from src.core.cache import cache
import torch

logger = logging.getLogger(__name__)

async def init_redis():
    """Inicializa conexão com Redis"""
    try:
        # Usar o novo sistema de cache
        await cache.connect()
        logger.info("Redis inicializado com sucesso")
        # Retornar a conexão do cache_manager
        return cache.get_connection()
    except Exception as e:
        logger.error(f"Erro inicializando Redis: {e}")
        raise

async def init_directories():
    """Cria diretórios necessários"""
    try:
        directories = [
            settings.TEMP_DIR,
            settings.MEDIA_DIR,
            settings.CACHE_DIR,
            settings.MODELS_DIR,
            settings.MODELS_BASE_DIR / "fish_speech",
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
    """Inicializa serviços básicos"""
    try:
        # Inicializar serviços em paralelo
        await asyncio.gather(
            init_redis_pool(),
            setup_monitoring(),
            init_directories()
        )
        
        # Verificar GPUs
        if torch.cuda.is_available():
            logger.info(f"GPUs disponíveis: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                logger.info(f"GPU {i}: {props.name} ({props.total_memory/1e9:.1f}GB)")
        else:
            logger.warning("Nenhuma GPU disponível, usando CPU")
            
        logger.info("✅ API iniciada")
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
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

async def initialize_services():
    """Inicializa todos os serviços necessários"""
    try:
        await setup_monitoring()  # ou com uma porta específica: await setup_monitoring(port=8000)
        # ... outras inicializações ...
    except Exception as e:
        logger.error(f"Erro na inicialização dos serviços: {e}")
        raise 