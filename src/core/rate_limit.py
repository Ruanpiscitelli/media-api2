"""
Módulo para controle de rate limiting usando Redis.
Implementa política de degradação graciosa quando Redis indisponível.
"""

from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.core.config import settings
import redis
import logging
from typing import Optional
from datetime import datetime, timedelta
import time
from functools import lru_cache

logger = logging.getLogger(__name__)

class RateLimitError(Exception):
    """Exceção customizada para erros de rate limiting"""
    pass

class RedisManager:
    """
    Gerenciador de conexão Redis com singleton pattern
    """
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisManager, cls).__new__(cls)
        return cls._instance

    def get_client(self) -> Optional[redis.Redis]:
        """
        Retorna cliente Redis existente ou tenta criar novo
        """
        if self._client is not None:
            try:
                self._client.ping()
                return self._client
            except:
                self._client = None
        
        self._client = self._create_client()
        return self._client

    def _create_client(self) -> Optional[redis.Redis]:
        """
        Cria nova conexão com Redis com retry
        """
        max_retries = 3
        retry_delay = 1  # segundos
        
        for attempt in range(max_retries):
            try:
                client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=settings.REDIS_PASSWORD,
                    db=settings.REDIS_DB,
                    socket_timeout=settings.REDIS_TIMEOUT,
                    decode_responses=True,
                    ssl=settings.REDIS_SSL
                )
                client.ping()  # Testa conexão
                return client
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Erro conectando ao Redis após {max_retries} tentativas: {e}")
                time.sleep(retry_delay)
        return None

def get_limiter() -> Limiter:
    """
    Factory function para criar e configurar o limiter.
    Evita problemas de importação circular e inicialização prematura.
    """
    redis_manager = RedisManager()
    redis_client = redis_manager.get_client()
    
    if redis_client is None:
        logger.critical("Redis indisponível - Rate limiting pode não funcionar corretamente")
        
    return Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
        storage_uri=f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}"
    )

# Criar instância do limiter usando a factory function
limiter = get_limiter()

async def rate_limiter(request: Request):
    """
    Middleware para controle de rate limiting com degradação graciosa.
    
    Em caso de falha do Redis:
    - Logs detalhados são gerados
    - Em produção: retorna 503
    - Em desenvolvimento: permite request com warning
    - Métricas de falha são registradas para monitoramento
    
    Args:
        request: Request do FastAPI
        
    Raises:
        HTTPException: Se o limite de requisições for excedido ou serviço indisponível
    """
    try:
        redis_manager = RedisManager()
        redis_client = redis_manager.get_client()
        
        if redis_client is None:
            logger.error("Redis indisponível - Rate limiting degradado")
            request.state.rate_limit_degraded = True
            
            if settings.ENVIRONMENT == "production":
                raise HTTPException(
                    status_code=503,
                    detail="Rate limiting service unavailable"
                )
            return

        # Obter IP do cliente
        client_ip = get_remote_address(request)
        
        # Chave única para o cliente
        key = f"rate_limit:{client_ip}"
        
        # Usar pipeline do Redis para operações atômicas
        with redis_client.pipeline() as pipe:
            pipe.multi()
            pipe.incr(key)
            pipe.ttl(key)
            requests, ttl = pipe.execute()
            
            # Se primeira requisição ou TTL expirou, definir TTL
            if ttl < 0:
                redis_client.expire(key, 60)  # 60 segundos
                
            # Se excedeu limite
            if requests > settings.RATE_LIMIT_PER_MINUTE:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Too many requests",
                        "retry_after": ttl if ttl > 0 else 60
                    }
                )
            
    except redis.RedisError as e:
        logger.error(f"Erro no Redis durante rate limiting: {e}")
        request.state.rate_limit_error = str(e)
        
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=503,
                detail="Rate limiting service unavailable"
            )
    
    except Exception as e:
        logger.error(f"Erro crítico no rate limiting: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        ) 