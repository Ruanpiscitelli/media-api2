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
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
import secrets
import redis
from redis.asyncio import Redis
import redis.asyncio
from src.core.rate_limit import rate_limiter
from src.core.config import settings
from src.core.checks import run_system_checks
from src.comfy.workflow_manager import ComfyWorkflowManager
from src.core.gpu.manager import GPUManager
from src.core.queue.manager import QueueManager

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
        yield
    finally:
        # Shutdown
        await shutdown_tasks()

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

# Executar verificações antes de iniciar
run_system_checks()

# Configurar aplicação FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Range", "Range"],
        max_age=3600,
    )

setup_cors()

# Middleware para verificar origens
@app.middleware("http")
async def cors_origin_middleware(request: Request, call_next):
    """Middleware para verificar origens CORS."""
    origin = request.headers.get("origin")
    if origin and origin not in settings.BACKEND_CORS_ORIGINS:
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

async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    endpoint = request.url.path
    key = f"rate_limit:{client_ip}:{endpoint}"
    
    # Adicionar diferentes limites por endpoint
    limit = settings.RATE_LIMITS.get(endpoint, settings.DEFAULT_RATE_LIMIT)
    
    async with redis_client.pipeline(transaction=True) as pipe:
        current = await pipe.incr(key)
        if current == 1:
            await pipe.expire(key, 60)
        await pipe.execute()
        
    if current > limit:
        raise HTTPException(
            status_code=429, 
            detail={
                "error": "Too many requests",
                "limit": limit,
                "reset": await redis_client.ttl(key)
            }
        )

app.middleware("http")(rate_limit_middleware)

app.add_middleware(
    ErrorHandlerMiddleware,
    handlers={
        500: handle_gpu_errors,
        429: handle_rate_limit
    }
)

# Instanciar managers
workflow_manager = ComfyWorkflowManager()
gpu_manager = GPUManager()
queue_manager = QueueManager()

@app.post("/v2/comfy/execute", tags=["ComfyUI"])
async def execute_workflow(
    workflow_request: WorkflowExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """
    Executa um workflow do ComfyUI.
    
    - Valida o workflow
    - Aloca recursos (GPU)
    - Executa em background
    - Retorna ID para acompanhamento
    """
    try:
        # Validar workflow
        if not await workflow_manager.validate_workflow(workflow_request.workflow):
            raise HTTPException(400, "Workflow inválido")
            
        # Estimar recursos necessários
        resources = await gpu_manager.estimate_resources(workflow_request.workflow)
        if not resources:
            raise HTTPException(500, "Falha ao estimar recursos necessários")
            
        # Alocar GPU
        gpu_id = await gpu_manager.allocate_gpu(
            task_id=str(uuid.uuid4()),  # Gerar ID único para a tarefa
            vram_required=resources["vram_required"],
            priority=workflow_request.priority
        )
        
        if gpu_id is None:
            raise HTTPException(503, "Nenhuma GPU disponível")
            
        # Criar tarefa
        task_id = await queue_manager.create_task(
            workflow=workflow_request.workflow,
            user_id=current_user.id,
            gpu_id=gpu_id,
            priority=workflow_request.priority
        )
        
        # Executar em background
        background_tasks.add_task(
            workflow_manager.execute_workflow,
            workflow=workflow_request.workflow,
            prompt_inputs=workflow_request.inputs,
            client_id=task_id
        )
        
        return {
            "task_id": task_id,
            "status": "queued",
            "estimated_time": resources["estimated_time"],
            "gpu_id": gpu_id
        }
        
    except Exception as e:
        logger.error(f"Erro executando workflow: {e}")
        raise HTTPException(500, str(e))

@app.get("/v2/comfy/workflows")
async def list_workflows(current_user = Depends(get_current_user)):
    """Lista workflows disponíveis"""
    workflows = []
    for path in Path("workflows").glob("*.json"):
        with open(path) as f:
            workflow = json.load(f)
            workflows.append({
                "name": path.stem,
                "description": workflow.get("description"),
                "created_at": path.stat().st_mtime
            })
    return {"workflows": workflows}

@app.post("/v2/comfy/workflows/{name}")
async def save_workflow(
    name: str,
    workflow: Dict,
    current_user = Depends(get_current_user)
):
    """Salva um novo workflow"""
    try:
        # Validar workflow
        if not await workflow_manager.validate_workflow(workflow):
            raise HTTPException(400, "Workflow inválido")
            
        # Salvar
        path = Path("workflows") / f"{name}.json"
        with open(path, "w") as f:
            json.dump(workflow, f, indent=2)
            
        return {"status": "success"}
        
    except Exception as e:
        raise HTTPException(500, str(e))

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