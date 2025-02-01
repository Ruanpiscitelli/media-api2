"""
Módulo para controle de rate limiting usando Redis.
"""

from fastapi import Request, HTTPException, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.core.config import settings
import redis
import logging

logger = logging.getLogger(__name__)

# Configurar conexão Redis
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True
)

# Configurar limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
)

async def rate_limiter(request: Request):
    """
    Middleware para controle de rate limiting.
    
    Args:
        request: Request do FastAPI
        
    Raises:
        HTTPException: Se o limite de requisições for excedido
    """
    try:
        # Obter IP do cliente
        client_ip = get_remote_address(request)
        
        # Chave única para o cliente
        key = f"rate_limit:{client_ip}"
        
        # Verificar limite
        requests = redis_client.incr(key)
        
        # Se primeira requisição, definir TTL
        if requests == 1:
            redis_client.expire(key, 60)  # 60 segundos
            
        # Se excedeu limite
        if requests > settings.RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail="Too many requests"
            )
            
    except redis.RedisError as e:
        logger.error(f"Erro no Redis: {e}")
        # Em caso de erro no Redis, permite a requisição
        pass
    
    except Exception as e:
        logger.error(f"Erro no rate limiting: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        ) 