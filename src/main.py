"""
Servidor principal da API de geração de mídia.
Gerencia inicialização, configuração e ciclo de vida da aplicação.
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, UJSONResponse
from fastapi.security import OAuth2PasswordBearer
from contextlib import asynccontextmanager
import logging
import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
import psutil
import torch
from datetime import datetime
from src.services.comfy_server import get_comfy_server, ComfyServer
from src.comfy.template_manager import TemplateManager

# Core imports
from src.core.config import settings
from src.core.rate_limit import rate_limiter
from src.core.checks import run_system_checks
from src.core.monitoring import REQUEST_COUNT, REQUEST_LATENCY
from src.core.redis_client import close_redis_pool, init_redis_pool
from src.core.middleware.connection import ConnectionMiddleware
from src.core.initialization import cache_manager
from src.services.image import get_image_service
from src.services.video import get_video_service

# Routers
from src.api.v2.endpoints import (
    processing,
    templates,
    json2video,
    suno,
    shorts,
    images,
    audio,
    video,
    comfy,
    fish_speech,
    models,
    workflows,
    jobs,
    auth,
    users,
    settings as settings_router,
    monitoring
)

# Configurar logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=settings.LOG_LEVEL)

# Scheduler global
scheduler = AsyncIOScheduler()

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    # Startup
    try:
        # Inicializar Redis
        await init_redis_pool()
        
        # Iniciar scheduler
        scheduler.start()
        
        logger.info("API iniciada com sucesso")
        yield
        
    except Exception as e:
        logger.error(f"Erro durante inicialização: {e}")
        raise
    finally:
        # Shutdown
        scheduler.shutdown()
        await close_redis_pool()
        logger.info("API finalizada")

# Middleware de segurança
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Adicionar headers de segurança
        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "X-Process-Time": str(process_time)
        })
        
        # Registrar métricas
        REQUEST_LATENCY.observe(process_time)
        
        return response

# Configurar aplicação FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API para processamento de mídia com múltiplas GPUs",
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    debug=settings.DEBUG,
    default_response_class=UJSONResponse,
    lifespan=lifespan
)

# Adicionar middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ConnectionMiddleware)
app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SECRET_KEY,
    same_site="lax",  # Proteção contra CSRF
    https_only=True   # Cookies apenas via HTTPS
)

# Middleware de rate limiting
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    try:
        if not getattr(request.state, "skip_rate_limit", False):
            await rate_limiter.is_rate_limited(request)
        return await call_next(request)
    except HTTPException as e:
        if e.status_code == 429:
            return JSONResponse(
                status_code=429, 
                content={"detail": e.detail}
            )
        raise

# Middleware de métricas
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    REQUEST_COUNT.inc()
    response = await call_next(request)
    return response

# Incluir routers com prefixo de versão
API_V2_PREFIX = "/api/v2"

routers = [
    (processing.router, "Processing"),
    (templates.router, "Templates"),
    (json2video.router, "JSON2Video"),
    (suno.router, "Suno"),
    (shorts.router, "Shorts"),
    (images.router, "Images"),
    (audio.router, "Audio"),
    (video.router, "Video"),
    (comfy.router, "ComfyUI"),
    (fish_speech.router, "FishSpeech"),
    (models.router, "Models"),
    (workflows.router, "Workflows"),
    (jobs.router, "Jobs"),
    (auth.router, "Auth"),
    (users.router, "Users"),
    (settings_router.router, "Settings"),
    (monitoring.router, "Monitoring")
]

for router, tag in routers:
    app.include_router(router, prefix=API_V2_PREFIX, tags=[tag])

# Dependency para injetar o ComfyServer
async def get_comfy():
    return await get_comfy_server()

@asynccontextmanager
async def get_comfy_context():
    comfy = await get_comfy_server()
    try:
        yield comfy
    finally:
        await comfy.close()

@app.on_event("startup")
async def startup_event():
    """Inicializa serviços na startup da API"""
    try:
        # Executar verificações do sistema
        run_system_checks()
        logger.info("✅ Verificações do sistema concluídas")
        
        # Inicializar cache
        await cache_manager.ensure_connection()
        logger.info("✅ Cache inicializado")
        
        # Inicializar serviços
        await get_image_service()
        await get_video_service()
        logger.info("✅ Serviços inicializados")
        
        # Inicializar ComfyUI
        comfy = await get_comfy_server()
        if not await comfy.verify_connection():
            logger.error("❌ Não foi possível conectar ao ComfyUI")
            raise RuntimeError("ComfyUI não está acessível")
        logger.info("✅ Conexão com ComfyUI estabelecida")
        
    except Exception as e:
        logger.error(f"❌ Erro na inicialização: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Limpa recursos na finalização da API"""
    try:
        comfy = await get_comfy_server()
        await comfy.close()
        logger.info("✅ Conexão com ComfyUI fechada")
    except Exception as e:
        logger.error(f"❌ Erro no shutdown: {e}")

@app.get("/health")
async def health_check(comfy: ComfyServer = Depends(get_comfy)):
    """
    Endpoint para verificar status da API com monitoramento detalhado do sistema.
    Retorna informações sobre serviços, recursos e métricas.
    """
    try:
        start_time = time.time()
        health_data = {
            "status": "healthy",
            "version": settings.VERSION,
            "services": {},
            "resources": {},
            "metrics": {},
            "timestamp": datetime.utcnow().isoformat()
        }

        # Verificar ComfyUI
        try:
            comfy_status = await comfy.get_status()
            health_data["services"]["comfy"] = {
                "status": "ok" if comfy_status.get('ready', False) else "error",
                "details": comfy_status
            }
        except Exception as e:
            health_data["services"]["comfy"] = {"status": "error", "error": str(e)}

        # Verificar GPUs
        try:
            gpu_info = []
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    gpu = torch.cuda.get_device_properties(i)
                    allocated = torch.cuda.memory_allocated(i)
                    reserved = torch.cuda.memory_reserved(i)
                    
                    gpu_info.append({
                        "id": i,
                        "name": gpu.name,
                        "memory": {
                            "total": gpu.total_memory,
                            "allocated": allocated,
                            "reserved": reserved,
                            "available": gpu.total_memory - allocated,
                            "utilization": (allocated / gpu.total_memory) * 100
                        },
                        "compute_capability": f"{gpu.major}.{gpu.minor}"
                    })

            health_data["resources"]["gpu"] = {
                "available": torch.cuda.is_available(),
                "count": len(gpu_info),
                "devices": gpu_info
            }
        except Exception as e:
            health_data["resources"]["gpu"] = {"status": "error", "error": str(e)}

        # Verificar recursos do sistema
        try:
            # CPU
            cpu_info = {
                "percent": psutil.cpu_percent(interval=1),
                "count": {
                    "physical": psutil.cpu_count(logical=False),
                    "logical": psutil.cpu_count()
                },
                "frequency": {
                    "current": psutil.cpu_freq().current if psutil.cpu_freq() else None,
                    "min": psutil.cpu_freq().min if psutil.cpu_freq() else None,
                    "max": psutil.cpu_freq().max if psutil.cpu_freq() else None
                },
                "load_average": psutil.getloadavg()
            }
            health_data["resources"]["cpu"] = cpu_info

            # Memória
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            health_data["resources"]["memory"] = {
                "system": {
                    "total": memory.total / (1024**3),  # GB
                    "available": memory.available / (1024**3),
                    "used": memory.used / (1024**3),
                    "percent": memory.percent
                },
                "swap": {
                    "total": swap.total / (1024**3),
                    "used": swap.used / (1024**3),
                    "free": swap.free / (1024**3),
                    "percent": swap.percent
                }
            }

            # Disco
            disk = psutil.disk_usage('/')
            health_data["resources"]["disk"] = {
                "total": disk.total / (1024**3),
                "used": disk.used / (1024**3),
                "free": disk.free / (1024**3),
                "percent": disk.percent
            }
        except Exception as e:
            health_data["resources"]["system"] = {"status": "error", "error": str(e)}

        # Métricas da aplicação
        health_data["metrics"] = {
            "response_time": time.time() - start_time,
            "uptime": time.time() - psutil.Process().create_time()
        }

        # Verificar status geral
        if any(
            service.get("status") == "error" 
            for service in health_data["services"].values()
        ):
            health_data["status"] = "unhealthy"
            return JSONResponse(status_code=503, content=health_data)

        return health_data

    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }