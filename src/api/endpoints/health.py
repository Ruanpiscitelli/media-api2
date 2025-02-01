from fastapi import APIRouter, Depends
from src.core.database import Database
from src.core.redis import Redis
from src.core.gpu import GPUManager
from src.core.server import ComfyUIServer
from src.core.cache import CacheService

app = APIRouter()

@app.get("/health")
async def full_health_check(
    db: Database = Depends(get_db),
    redis: Redis = Depends(get_redis),
    gpu_manager: GPUManager = Depends(get_gpu_manager),
    comfy_server: ComfyUIServer = Depends(get_comfy_server),
    cache_service: CacheService = Depends(get_cache_service)
):
    checks = {
        "database": await check_db_connection(db),
        "redis": await check_redis_connection(redis),
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
        "services": {
            "comfyui": comfy_server.is_ready(),
            "cache": cache_service.is_healthy()
        }
    }
    
    return checks 