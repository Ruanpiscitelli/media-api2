"""
Servidor principal da API de geração de mídia.
Gerencia inicialização, configuração e ciclo de vida da aplicação.
"""

from fastapi import FastAPI, Request, Response, BackgroundTasks, Depends, HTTPException
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
from typing import List, Dict
from fastapi import Header
import torch
import asyncio
import json
import psutil
import gc
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
import secrets
import redis
from redis.asyncio import Redis
import redis.asyncio

from src.core.rate_limit import limiter
from src.core.config import settings
from src.core.checks import run_system_checks
from src.comfy.workflow_manager import ComfyWorkflowManager
from src.core.gpu.manager import GPUManager
from src.core.queue.manager import QueueManager
from src.core.initialization import initialize_api
from src.core.errors import APIError, api_error_handler, validation_error_handler
from src.core.monitoring import REQUEST_COUNT, REQUEST_LATENCY
from src.core.redis_client import close_redis_pool

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
from src.services.auth import get_current_user

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
        await startup_tasks()
        await initialize_api()
        yield
    finally:
        # Shutdown
        await shutdown_tasks()
        await close_redis_pool()

async def shutdown_tasks():
    """Tarefas de shutdown melhoradas"""
    logger.info("Iniciando shutdown gracioso...")
    
    # Parar de aceitar novas requisições
    app.state.accepting_requests = False
    
    # Aguardar requisições em andamento (com timeout)
    try:
        await asyncio.wait_for(
            asyncio.gather(*app.state.running_tasks),
            timeout=30
        )
    except asyncio.TimeoutError:
        logger.warning("Timeout aguardando requisições terminarem")
    
    # Parar scheduler
    scheduler.shutdown(wait=True)
    
    # Fechar conexões do banco
    await engine.dispose()
    
    # Fechar conexões Redis
    await redis_client.close()
    await aioredis_pool.disconnect()
    
    # Limpar recursos GPU
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    # Forçar coleta de lixo
    gc.collect()
    
    logger.info("Shutdown concluído")

# Configurar logger
logger = setup_logging()

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

# Executar verificações antes de iniciar
run_system_checks()

# Configurar aplicação FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    debug=settings.DEBUG,
    # Otimizações de performance
    default_response_class=JSONResponse,
    generate_unique_id_function=None,  # Desativa geração de IDs únicos
    lifespan=lifespan
)

# Middleware de rate limiting
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Middleware para aplicar rate limiting."""
    try:
        # Verifica se a rota deve ser limitada
        if not getattr(request.state, "skip_rate_limit", False):
            await limiter.is_rate_limited(request)
        return await call_next(request)
    except HTTPException as e:
        if e.status_code == 429:  # Too Many Requests
            return JSONResponse(
                status_code=429,
                content=e.detail
            )
        raise

# Middleware de métricas
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Coleta métricas de requisições."""
    start_time = time.time()
    
    # Incrementa contador de requisições
    REQUEST_COUNT.inc()
    
    response = await call_next(request)
    
    # Registra latência
    REQUEST_LATENCY.observe(time.time() - start_time)
    
    return response

# Configurar CORS de forma otimizada
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Range"],  # Readicionado expose_headers
    max_age=3600,
)

# Incluir rotas de forma otimizada
app.include_router(
    api_v2_router,
    prefix=settings.API_V2_STR,
    # Desativar geração de tags automática
    generate_unique_id_function=None
)

# Montar arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")

# Middleware para timeout
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    try:
        return await asyncio.wait_for(
            call_next(request), 
            timeout=settings.REQUEST_TIMEOUT
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Request timeout"
        )

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
    app.include_router(processing.router, prefix=settings.API_V2_STR)
    app.include_router(templates.router, prefix=settings.API_V2_STR)
    
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

# Incluir rotas da GUI
from src.web.routes import router as web_router
from src.web.routes import gui_app

# Iniciar servidor GUI na porta 8080
import uvicorn
from multiprocessing import Process

def run_gui():
    uvicorn.run(gui_app, host="0.0.0.0", port=8080)

# Iniciar GUI em um processo separado
gui_process = Process(target=run_gui)
gui_process.start()

# Criar cliente Redis assíncrono
redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

@app.on_event("startup")
async def startup_event():
    """Verifica serviços necessários na inicialização"""
    # Verificar Redis
    try:
        is_connected = await redis_client.ping()
        if is_connected:
            logger.info("Redis conectado com sucesso")
        else:
            raise redis.RedisError("Falha na conexão com Redis - ping retornou False")
    except redis.RedisError as e:
        logger.error(f"Erro ao conectar ao Redis: {e}")
        raise

    # Verificar diretórios
    for path in [settings.TEMP_DIR, settings.SUNO_OUTPUT_DIR, settings.SUNO_CACHE_DIR]:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Diretório criado: {path}")

    # Iniciar scheduler
    scheduler.start()
    logger.info("Scheduler iniciado")

    # Validar configurações ao iniciar
    settings.check_config()

if __name__ == "__main__":
    import uvicorn
    
    # Configurações otimizadas do uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        workers=4,  # Número de workers baseado em CPUs
        loop="uvloop",  # Usar uvloop para melhor performance
        http="httptools",  # Usar httptools
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.DEBUG,
        reload_delay=0.25,  # Reduzir delay do reload
        access_log=settings.DEBUG,  # Desativar access_log em produção
        proxy_headers=True,
        forwarded_allow_ips="*",
        # Otimizações de buffer
        backlog=2048,
        limit_concurrency=1000,
        timeout_keep_alive=5,
    ) 