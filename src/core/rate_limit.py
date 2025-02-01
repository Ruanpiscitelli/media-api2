"""
Configuração de rate limiting usando Redis e Slowapi
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.core.config import settings

# Criar instância do limiter usando Redis como backend
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    strategy="fixed-window",  # Estratégia de janela fixa
    storage_options={
        "password": settings.REDIS_PASSWORD,
        "socket_timeout": 5,
        "socket_connect_timeout": 5
    }
)

# Exportar o limiter para uso nos endpoints
rate_limiter = limiter