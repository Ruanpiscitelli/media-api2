"""
Servidor principal da API de geração de mídia.
Gerencia inicialização, configuração e ciclo de vida da aplicação.
"""

from fastapi import FastAPI, Request, Response, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import time
import logging
import uuid
from datetime import datetime
from pathlib import Path
from fastapi.staticfiles import StaticFiles
import os
from typing import List
from fastapi import Header
import torch
import asyncio
import json
import psutil
import gc
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi.security import HTTPBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
import secrets

# Importação dos routers
from src.api.v2.endpoints import (
    # Core
    processing,
    templates,
    
    # Media Generation
    json2video,
    suno,
    shorts,
    images,
    audio,
    video,
    
    # Integrations
    comfy,
    fish_speech,
    
    # Management
    models,
    workflows,
    jobs,
    
    # System
    auth,
    users,
    settings,
    monitoring
)

# Importar configurações e serviços
from src.core.config import settings
from src.services.comfy_server import comfy_server
from src.comfy.template_manager import TemplateManager
from src.comfy.default_templates import get_default_templates

# Scheduler global
scheduler = AsyncIOScheduler()

# Funções de limpeza e monitoramento
async def cleanup_temp_files():
    """Limpa arquivos temporários antigos."""
    try:
        temp_dir = Path(settings.TEMP_DIR)
        current_time = time.time()
        
        for file_path in temp_dir.glob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > settings.TEMP_FILE_MAX_AGE:
                    file_path.unlink()
                    logger.info(f"Arquivo temporário removido: {file_path}")
    except Exception as e:
        logger.error(f"Erro na limpeza de arquivos temporários: {e}")

async def monitor_memory():
    """Monitora uso de memória e realiza limpeza se necessário."""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        
        # Converter para MB para melhor legibilidade
        memory_mb = memory_info.rss / 1024 / 1024
        logger.info(f"Uso de memória: {memory_mb:.2f}MB")
        
        # Se uso de memória ultrapassar limite, força garbage collection
        if memory_mb > settings.MEMORY_THRESHOLD_MB:
            gc.collect()
            torch.cuda.empty_cache()
            logger.info("Limpeza de memória realizada")
            
        # Monitorar GPU VRAM
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                allocated = torch.cuda.memory_allocated(i) / 1024 / 1024
                reserved = torch.cuda.memory_reserved(i) / 1024 / 1024
                logger.info(f"GPU {i} - Alocado: {allocated:.2f}MB, Reservado: {reserved:.2f}MB")
                
    except Exception as e:
        logger.error(f"Erro no monitoramento de memória: {e}")

# Criar diretórios necessários
def setup_directories():
    """Cria diretórios necessários para a aplicação."""
    directories = [
        settings.LOG_DIR,
        settings.MEDIA_DIR,
        settings.TEMP_DIR,
        settings.SHORTS_OUTPUT_DIR,
        settings.SHORTS_CACHE_DIR,
        settings.SHORTS_UPLOAD_DIR,
        "static",
        "templates"  # Diretório para templates
    ]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

# Configuração de logging
def setup_logging():
    """Configura o sistema de logging."""
    logging.basicConfig(
        level=logging.INFO if not settings.DEBUG else logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"{settings.LOG_DIR}/api.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Gerenciador de ciclo de vida da aplicação
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação.
    Inicializa recursos na startup e limpa na shutdown.
    """
    # Startup
    try:
        # Criar diretórios
        setup_directories()
        
        # Inicializar ComfyUI
        await comfy_server.initialize()
        
        # Inicializar templates padrão
        template_manager = TemplateManager()
        templates_initialized = False
        retry_count = 0
        max_retries = 3
        
        while not templates_initialized and retry_count < max_retries:
            try:
                default_templates = get_default_templates()
                for template in default_templates:
                    try:
                        template_manager.create_template(
                            name=template["name"],
                            description=template["description"],
                            workflow=template["workflow"],
                            parameters=template["parameters"],
                            parameter_mappings=template["parameter_mappings"],
                            author="system",
                            tags=template["tags"],
                            category=template["category"]
                        )
                        logger.info(f"Template {template['name']} inicializado com sucesso")
                    except ValueError as e:
                        if "já existe" not in str(e):
                            logger.error(f"Erro ao inicializar template {template['name']}: {e}")
                templates_initialized = True
            except Exception as e:
                retry_count += 1
                logger.error(f"Tentativa {retry_count} de inicializar templates falhou: {e}")
                await asyncio.sleep(2)
                
        if not templates_initialized:
            logger.error("Falha ao inicializar templates após várias tentativas")
        
        # Inicializar scheduler
        scheduler.add_job(cleanup_temp_files, 'interval', hours=1)
        scheduler.add_job(monitor_memory, 'interval', minutes=5)
        scheduler.start()
            
        logger.info("🚀 Aplicação inicializada com sucesso")
        
    except Exception as e:
        logger.error(f"❌ Erro fatal na inicialização: {e}")
        raise e
        
    yield
    
    # Shutdown
    try:
        # Parar scheduler
        scheduler.shutdown()
        
        # Limpar recursos
        await comfy_server.shutdown()
        
        # Forçar limpeza de memória
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        logger.info("👋 Aplicação finalizada com sucesso")
    except Exception as e:
        logger.error(f"❌ Erro no shutdown: {e}")

# Configurar logger
logger = setup_logging()

# Configurar rate limiter
limiter = Limiter(key_func=get_remote_address)
security = HTTPBearer()

# Middleware de segurança
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adiciona headers de segurança às respostas."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

# Configurar aplicação FastAPI
app = FastAPI(
    title="Media Generation API",
    description="API para geração de mídia com IA",
    version="2.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Adicionar middlewares de segurança
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY or secrets.token_urlsafe(32),
    max_age=3600,  # 1 hora
    same_site="lax",
    https_only=True
)

# Configurar rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Rate limiting global
@app.middleware("http")
@limiter.limit("60/minute")  # Limite global
async def global_rate_limit(request: Request, call_next):
    response = await call_next(request)
    return response

# Configurar CORS
def setup_cors():
    """Configura CORS para a aplicação."""
    origins = json.loads(os.environ.get("CORS_ORIGINS", '["http://localhost:3000"]'))
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"]
    )
    return origins

origins = setup_cors()

# Middleware para verificar origens
@app.middleware("http")
async def cors_origin_middleware(request: Request, call_next):
    """Middleware para verificar origens CORS."""
    origin = request.headers.get("origin")
    if origin and origin not in origins:
        return JSONResponse(
            status_code=400,
            content={"detail": "Origin not allowed"}
        )
    response = await call_next(request)
    return response

# Montar arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")

# Middleware para timeout
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    """Middleware para timeout de operações GPU."""
    if request.url.path.startswith("/api/v2/processing"):
        try:
            timeout = float(os.getenv("RENDER_TIMEOUT_SECONDS", settings.RENDER_TIMEOUT_SECONDS))
            response = await asyncio.wait_for(call_next(request), timeout=timeout)
            return response
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={
                    "detail": f"Operação excedeu o timeout de {timeout} segundos"
                }
            )
    return await call_next(request)

# Middleware para logging de requests
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Middleware para logging de requests."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(
        f"Method: {request.method} Path: {request.url.path} "
        f"Status: {response.status_code} Time: {process_time:.2f}s"
    )
    
    return response

# Registrar routers
def setup_routers():
    """Configura os routers da aplicação."""
    # Core
    app.include_router(processing.router)
    app.include_router(templates.router)
    
    # Media Generation
    app.include_router(json2video.router)
    app.include_router(suno.router)
    app.include_router(shorts.router)
    app.include_router(images.router)
    app.include_router(audio.router)
    app.include_router(video.router)
    
    # Integrations
    app.include_router(comfy.router)
    app.include_router(fish_speech.router)
    
    # Management
    app.include_router(models.router)
    app.include_router(workflows.router)
    app.include_router(jobs.router)
    
    # System
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(settings.router)
    app.include_router(monitoring.router)

setup_routers()

# Rota de health check
@app.get("/health", tags=["Sistema"])
async def health_check():
    """Verifica saúde do sistema"""
    try:
        start_time = time.time()
        health_data = {
            "status": "healthy",
            "services": {},
            "resources": {},
            "metrics": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Verificar status do ComfyUI
        try:
            comfy_status = await comfy_server.get_status()
            health_data["services"]["comfy"] = {
                "status": "ok" if comfy_status.get('ready', False) else "error",
                "details": comfy_status
            }
        except Exception as e:
            health_data["services"]["comfy"] = {
                "status": "error",
                "error": str(e)
            }
            
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
                        "compute_capability": f"{gpu.major}.{gpu.minor}",
                        "temperature": None  # TODO: Implementar leitura de temperatura
                    })
                    
            health_data["resources"]["gpu"] = {
                "available": torch.cuda.is_available(),
                "count": len(gpu_info),
                "devices": gpu_info
            }
        except Exception as e:
            health_data["resources"]["gpu"] = {
                "status": "error",
                "error": str(e)
            }
            
        # Verificar templates
        try:
            templates = template_manager.list_templates()
            health_data["services"]["templates"] = {
                "count": len(templates),
                "status": "ok" if len(templates) > 0 else "warning",
                "categories": {}
            }
            
            # Contar templates por categoria
            for template in templates:
                category = template.metadata.category or "uncategorized"
                if category not in health_data["services"]["templates"]["categories"]:
                    health_data["services"]["templates"]["categories"][category] = 0
                health_data["services"]["templates"]["categories"][category] += 1
                
        except Exception as e:
            health_data["services"]["templates"] = {
                "status": "error",
                "error": str(e)
            }
            
        # Verificar memória do sistema
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            system = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            health_data["resources"]["memory"] = {
                "process": {
                    "rss": memory_info.rss / 1024 / 1024,  # MB
                    "vms": memory_info.vms / 1024 / 1024,  # MB
                    "shared": memory_info.shared / 1024 / 1024,  # MB
                    "data": memory_info.data / 1024 / 1024  # MB
                },
                "system": {
                    "total": system.total / 1024 / 1024,  # MB
                    "available": system.available / 1024 / 1024,  # MB
                    "used": system.used / 1024 / 1024,  # MB
                    "percent": system.percent
                },
                "swap": {
                    "total": swap.total / 1024 / 1024,  # MB
                    "used": swap.used / 1024 / 1024,  # MB
                    "free": swap.free / 1024 / 1024,  # MB
                    "percent": swap.percent
                }
            }
        except Exception as e:
            health_data["resources"]["memory"] = {
                "status": "error",
                "error": str(e)
            }
            
        # Verificar CPU
        try:
            cpu_info = {
                "percent": psutil.cpu_percent(interval=1),
                "count": {
                    "physical": psutil.cpu_count(logical=False),
                    "logical": psutil.cpu_count()
                },
                "frequency": {
                    "current": psutil.cpu_freq().current,
                    "min": psutil.cpu_freq().min,
                    "max": psutil.cpu_freq().max
                },
                "load_average": psutil.getloadavg()
            }
            health_data["resources"]["cpu"] = cpu_info
        except Exception as e:
            health_data["resources"]["cpu"] = {
                "status": "error",
                "error": str(e)
            }
            
        # Verificar disco
        try:
            disk = psutil.disk_usage('/')
            health_data["resources"]["disk"] = {
                "total": disk.total / 1024 / 1024 / 1024,  # GB
                "used": disk.used / 1024 / 1024 / 1024,  # GB
                "free": disk.free / 1024 / 1024 / 1024,  # GB
                "percent": disk.percent
            }
        except Exception as e:
            health_data["resources"]["disk"] = {
                "status": "error",
                "error": str(e)
            }
            
        # Métricas da aplicação
        health_data["metrics"] = {
            "response_time": time.time() - start_time,
            "uptime": time.time() - psutil.Process().create_time()
        }
        
        # Determinar status geral
        if any(service.get("status") == "error" for service in health_data["services"].values()):
            health_data["status"] = "unhealthy"
            return JSONResponse(status_code=503, content=health_data)
            
        return JSONResponse(status_code=200, content=health_data)
        
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# Middleware de timeout
class TimeoutMiddleware(BaseHTTPMiddleware):
    """Adiciona timeout às requisições."""
    
    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=settings.REQUEST_TIMEOUT
            )
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": "Request timeout"}
            )

app.add_middleware(TimeoutMiddleware)

# Middleware de logging melhorado
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log detalhado de requisições."""
    start_time = time.time()
    
    # Gerar ID único para a requisição
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Log inicial
    logger.info(f"Request {request_id} started: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        
        # Log de conclusão
        process_time = (time.time() - start_time) * 1000
        logger.info(
            f"Request {request_id} completed: {response.status_code} "
            f"({process_time:.2f}ms)"
        )
        
        # Adicionar headers de telemetria
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        
        return response
        
    except Exception as e:
        # Log de erro
        logger.error(f"Request {request_id} failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Configuração para debugging
    import uvicorn
    import debugpy
    
    # Habilita debugging remoto
    debugpy.listen(("0.0.0.0", 5678))
    
    # Configurações do servidor
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Habilita auto-reload para desenvolvimento
        debug=settings.DEBUG,
        workers=1  # Usar 1 worker para facilitar debugging
    ) 