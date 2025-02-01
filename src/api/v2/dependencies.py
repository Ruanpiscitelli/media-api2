"""
Dependências compartilhadas da API
"""
from fastapi import Request, HTTPException, Depends
from httpx import AsyncClient
from src.core.config import settings
from src.core.rate_limit import rate_limiter
import logging

logger = logging.getLogger(__name__)

# Errado ❌
def get_http_client(request: Request) -> AsyncClient:
    return request.state.client

# Correto ✅
async def get_http_client(request: Request) -> AsyncClient:
    return request.state.client

# Errado ❌
def get_current_user(request: Request):
    return request.state.user

# Correto ✅
async def get_current_user(request: Request):
    return request.state.user

async def rate_limit_dependency(request: Request):
    """Dependência para rate limiting"""
    try:
        # Obter chave do rate limit
        key = _get_rate_limit_key(request)
        
        # Obter limites para o endpoint
        limits = _get_endpoint_limits(request.url.path)
        
        # Verificar rate limit
        is_limited = await rate_limiter.is_rate_limited(
            key=key,
            limit=limits["limit"],
            window=limits["window"]
        )
        
        if is_limited:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Too Many Requests",
                    "reset": await rate_limiter.get_reset_time(key)
                }
            )
            
    except Exception as e:
        logger.error(f"Erro no rate limit: {e}")
        # Em caso de erro, permitir requisição
        return 