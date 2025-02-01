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
from src.core.monitoring import REQUESTS, ERRORS
from src.core.redis_client import close_redis_pool, init_redis_pool
from src.core.middleware.connection import ConnectionMiddleware
from src.core.initialization import initialize_api
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
        REQUESTS.inc()
        
        return response

# Configurar aplicação FastAPI
app = FastAPI(
    title="Media API",
    version="2.0.0",
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
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
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
    try:
        REQUESTS.inc()
        response = await call_next(request)
        return response
    except Exception as e:
        ERRORS.inc()
        logger.error(f"Erro: {e}")
        raise

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

# Startup
@app.on_event("startup")
async def startup():
    await initialize_api()

@app.get("/health")
async def health():
    return {"status": "ok"}