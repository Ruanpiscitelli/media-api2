"""
Main FastAPI application file

Este arquivo contém a configuração principal da API FastAPI, incluindo:
- Configuração do CORS
- Configuração do middleware de autenticação
- Configuração do middleware de rate limiting
- Registro dos routers
- Configuração de métricas Prometheus
- Configuração de logging OpenTelemetry
"""

import logging
from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import make_asgi_app
import os
import time

# Importação dos middlewares customizados
from .middleware.auth import AuthJWTMiddleware
from .middleware.rate_limit import RateLimitMiddleware

# Importação dos routers
from .endpoints import (
    images,  # Mudou de image para images
    video,
    speech,
    comfy,
    shorts,  # Adicionado novo router
    auth,    # Adicionado novo router
)

# Importação do servidor ComfyUI
from src.comfy.server import comfy_server

# Configuração da aplicação FastAPI
app = FastAPI(
    title="Media Generation API",
    description="API para geração de mídia usando IA",  # Simplificado para evitar erro de arquivo
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "images",
            "description": "Geração e processamento de imagens com IA"
        },
        {
            "name": "video",
            "description": "Síntese e edição de vídeos"
        },
        {
            "name": "shorts",
            "description": "Geração de YouTube Shorts"
        },
        {
            "name": "speech",
            "description": "Síntese de voz e áudio"
        },
        {
            "name": "auth",
            "description": "Autenticação e autorização"
        }
    ]
)

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de hosts confiáveis
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Em produção, especificar os hosts permitidos
)

# Adiciona middleware de autenticação JWT
app.add_middleware(AuthJWTMiddleware)

# Adiciona middleware de rate limiting baseado em Redis
app.add_middleware(RateLimitMiddleware)

# Configuração do endpoint de métricas Prometheus
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Evento de startup para iniciar o ComfyUI
@app.on_event("startup")
async def startup_event():
    """Inicializa o servidor ComfyUI durante o startup da API"""
    try:
        await comfy_server.start()
        await comfy_server.wait_until_ready(timeout=30)
        logger.info("ComfyUI iniciado com sucesso")
    except Exception as e:
        logger.error(f"Falha na inicialização do ComfyUI: {e}")
        raise RuntimeError("Servidor ComfyUI não inicializado")

# Evento de shutdown para parar o ComfyUI
@app.on_event("shutdown")
async def shutdown_event():
    """Para o servidor ComfyUI durante o shutdown da API"""
    await comfy_server.stop()
    logger.info("ComfyUI parado com sucesso")

# Handlers de erro
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Erro não tratado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erro interno do servidor",
            "type": type(exc).__name__,
            "path": request.url.path
        }
    )

@app.exception_handler(ConnectionError)
async def redis_connection_error(request: Request, exc: ConnectionError):
    """Trata erros de conexão com Redis"""
    logger.error(f"Erro de conexão com Redis: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Serviço temporariamente indisponível"}
    )

# Rota de healthcheck
@app.get("/health")
async def health_check():
    """
    Endpoint de healthcheck que retorna o status da API
    e informações básicas sobre o sistema
    """
    return {
        "status": "healthy",
        "version": "2.0.0",
        "environment": os.getenv("ENVIRONMENT", "production")
    }

# Registro dos routers
app.include_router(images.router, prefix="/v2/images", tags=["images"])
app.include_router(video.router, prefix="/v2/video", tags=["video"])
app.include_router(speech.router, prefix="/v2/speech", tags=["speech"])
app.include_router(comfy.router, prefix="/v2/comfy", tags=["comfy"])
app.include_router(shorts.router, prefix="/v2/shorts", tags=["shorts"])
app.include_router(auth.router, prefix="/v2/auth", tags=["auth"])

async def get_api_version(x_api_version: str = Header(default="v2")):
    if x_api_version not in ["v1", "v2"]:
        raise HTTPException(status_code=400, detail="Versão de API inválida")
    return x_api_version

# Exemplo de uso em um endpoint
@app.get("/test")
async def test_endpoint(version: str = Depends(get_api_version)):
    return {"version": version}

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.2f}s"
    )
    
    return response

@app.middleware("http")
async def handle_legacy_image_routes(request: Request, call_next):
    """
    Middleware para redirecionar requisições antigas de /v2/image para /v2/images
    mantendo compatibilidade com clientes existentes
    """
    if request.url.path.startswith("/v2/image/"):
        new_path = request.url.path.replace("/v2/image/", "/v2/images/", 1)
        return RedirectResponse(url=new_path, status_code=308)
    return await call_next(request)

@app.middleware("http")
async def check_redis_health(request: Request, call_next):
    """Verifica saúde do Redis antes de cada requisição"""
    try:
        redis = await get_redis()
        await redis.ping()
        return await call_next(request)
    except Exception as e:
        logger.error(f"Redis não está saudável: {e}")
        return JSONResponse(
            status_code=503,
            content={"detail": "Serviço temporariamente indisponível"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info") 