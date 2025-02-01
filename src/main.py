"""
Servidor principal da API de geração de mídia.
Gerencia inicialização, configuração e ciclo de vida da aplicação.
"""

from fastapi import FastAPI, Request
import asyncio
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
from src.core.monitoring import REQUESTS, ERRORS, REQUEST_LATENCY
from src.core.redis_client import close_redis_pool, init_redis_pool
from src.core.middleware.connection import ConnectionMiddleware
from src.core.initialization import initialize_api
from src.services.image import get_image_service
from src.services.video import get_video_service
from src.core.middleware.timeout import TimeoutMiddleware

# Configurar logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=settings.LOG_LEVEL)

# Scheduler global
scheduler = AsyncIOScheduler()

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

import sys
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciamento otimizado do ciclo de vida"""
    # Startup
    try:
        # Inicializar recursos em paralelo
        init_tasks = {
            'Redis Pool': init_redis_pool(),
            'Monitoring': setup_monitoring(),
            'Directories': init_directories()
        }
        
        results = await asyncio.gather(*init_tasks.values(), return_exceptions=True)
        
        # Verificar resultados
        for (name, _), result in zip(init_tasks.items(), results):
            if isinstance(result, Exception):
                logger.error(f"Falha em {name}: {result}")
            else:
                logger.info(f"✅ {name} OK")
        
        # Iniciar scheduler com retry
        for attempt in range(3):
            try:
                scheduler.start()
                break
            except Exception as e:
                if attempt == 2:
                    raise
                logger.warning(f"Tentativa {attempt + 1} de iniciar scheduler falhou: {e}")
                await asyncio.sleep(1)
        
        logger.info("✅ API iniciada com sucesso")
        yield
        
    except Exception as e:
        logger.error(f"❌ Erro durante inicialização: {e}")
        raise
    finally:
        # Shutdown limpo
        shutdown_tasks = {
            'Scheduler': scheduler.shutdown(),
            'Redis Pool': close_redis_pool()
        }
        
        results = await asyncio.gather(*shutdown_tasks.values(), return_exceptions=True)
        for (name, _), result in zip(shutdown_tasks.items(), results):
            if isinstance(result, Exception):
                logger.error(f"Erro ao finalizar {name}: {result}")
                
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
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    default_response_class=UJSONResponse
)

# Middlewares básicos
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
app.add_middleware(TimeoutMiddleware, timeout=300)

# Middleware de rate limit
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    try:
        if not getattr(request.state, "skip_rate_limit", False):
            await rate_limiter(request)
        return await call_next(request)
    except HTTPException as e:
        if e.status_code == 429:
            return JSONResponse(
                status_code=429,
                content={"detail": e.detail}
            )
        raise

# Middleware de métricas otimizado
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware para coletar métricas de performance"""
    path = request.url.path
    method = request.method
    start_time = time.time()
    
    try:
        # Incrementar contador de requests
        REQUESTS.labels(path=path, method=method).inc()
        
        # Executar request
        response = await call_next(request)
        
        # Registrar latência
        process_time = time.time() - start_time
        REQUEST_LATENCY.labels(path=path, method=method, status=response.status_code).observe(process_time)
        
        return response
    except Exception as e:
        # Registrar erros
        ERRORS.labels(path=path, method=method, error=type(e).__name__).inc()
        logger.error(f"Request error: {str(e)}", exc_info=True)
        raise

# Importar routers
from src.api.v2.endpoints import router_groups
for router, tags in router_groups:
    app.include_router(router, prefix="/api/v2", tags=tags)

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
    """Inicialização otimizada da API"""
    try:
        # Inicializar serviços em paralelo
        init_tasks = {
            'System Check': check_system(),
            'Database Check': check_db_connection(),
            'Redis Check': check_redis_connection(),
            'Redis Pool': init_redis_pool(),
            'Monitoring': setup_monitoring()
        }
        
        results = await asyncio.gather(*init_tasks.values(), return_exceptions=True)
        
        # Verificar resultados
        critical_services = ['System Check', 'Database Check', 'Redis Check']
        critical_failures = 0
        
        for (name, _), result in zip(init_tasks.items(), results):
            if isinstance(result, Exception):
                logger.error(f"Falha em {name}: {result}")
                if name in critical_services:
                    critical_failures += 1
            else:
                logger.info(f"✅ {name} OK")
                
        # Verificar se podemos continuar
        if critical_failures > 0:
            logger.warning(f"API iniciando com recursos limitados - {critical_failures} falhas críticas")
            
        logger.info("API iniciada")
    except Exception as e:
        logger.error(f"Erro na inicialização: {e}")
        raise

@app.get("/health")
async def health_check():
    """Endpoint para verificar saúde da API"""
    try:
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {}
        }
        
        # Verificar Redis de forma assíncrona
        try:
            if redis_pool:
                async with redis_pool.get() as redis:
                    await redis.ping()
                health["services"]["redis"] = "ok"
        except:
            health["services"]["redis"] = "error"
            
        # Verificar GPUs
        try:
            if torch.cuda.is_available():
                health["services"]["gpu"] = {
                    "count": torch.cuda.device_count(),
                    "devices": [
                        {
                            "id": i,
                            "name": torch.cuda.get_device_name(i),
                            "memory": torch.cuda.get_device_properties(i).total_memory
                        }
                        for i in range(torch.cuda.device_count())
                    ]
                }
            else:
                health["services"]["gpu"] = "cpu_only"
        except:
            health["services"]["gpu"] = "error"
            
        # Verificar espaço em disco
        try:
            disk = psutil.disk_usage("/workspace")
            health["services"]["disk"] = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            }
        except:
            health["services"]["disk"] = "error"
            
        return health
    except Exception as e:
        logger.error(f"Health check falhou: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }