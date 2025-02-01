"""
Endpoint unificado de health check do sistema.
Consolida todas as verificações de saúde em um único lugar.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import logging
from typing import Dict, Any

from src.core.database import Database, get_db
from src.core.redis import Redis, get_redis
from src.core.gpu import GPUManager, get_gpu_manager
from src.core.server import ComfyUIServer, get_comfy_server
from src.core.cache import CacheService, get_cache_service
from src.services.system import SystemService

router = APIRouter()
logger = logging.getLogger(__name__)
system_service = SystemService()

@router.get("/health")
async def health_check(
    db: Database = Depends(get_db),
    redis: Redis = Depends(get_redis),
    gpu_manager: GPUManager = Depends(get_gpu_manager),
    comfy_server: ComfyUIServer = Depends(get_comfy_server),
    cache_service: CacheService = Depends(get_cache_service)
) -> Dict[str, Any]:
    """
    Health check unificado que verifica todos os componentes do sistema.
    
    Returns:
        Dict com status de todos os componentes e métricas relevantes
    
    Raises:
        HTTPException: Se algum componente crítico estiver indisponível
    """
    try:
        # Verifica ComfyUI
        comfy_status = await comfy_server.get_status()
        if not comfy_status.get('ready', False):
            raise HTTPException(
                status_code=503,
                detail="ComfyUI não está pronto"
            )

        # Coleta todos os status
        checks = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": await check_db_connection(db),
                "redis": await check_redis_connection(redis),
                "cache": await cache_service.is_healthy(),
                "comfyui": comfy_status
            },
            "gpus": [
                {
                    "id": gpu.id,
                    "status": await gpu.get_status(),
                    "vram": {
                        "total": gpu.total_vram,
                        "used": gpu.used_vram,
                        "free": gpu.free_vram
                    }
                } for gpu in gpu_manager.gpus
            ],
            "system": await system_service.get_status()
        }
        
        return checks

    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Sistema indisponível: {str(e)}"
        )

async def check_db_connection(db: Database) -> Dict[str, Any]:
    """Verifica conexão com banco de dados"""
    try:
        await db.execute("SELECT 1")
        return {"status": "connected", "latency_ms": await db.get_latency()}
    except Exception as e:
        logger.error(f"Erro na conexão com banco: {e}")
        return {"status": "error", "error": str(e)}

async def check_redis_connection(redis: Redis) -> Dict[str, Any]:
    """Verifica conexão com Redis"""
    try:
        await redis.ping()
        return {
            "status": "connected",
            "used_memory": await redis.info('used_memory'),
            "connected_clients": await redis.info('connected_clients')
        }
    except Exception as e:
        logger.error(f"Erro na conexão com Redis: {e}")
        return {"status": "error", "error": str(e)} 