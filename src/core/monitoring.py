"""
Configuração de monitoramento usando Prometheus
"""
from prometheus_client import Counter, Histogram, start_http_server
import logging
import anyio
from anyio.to_thread import current_default_thread_limiter
import asyncio
import socket

logger = logging.getLogger(__name__)

# Métricas básicas
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total de requisições HTTP',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'Latência das requisições HTTP',
    ['method', 'endpoint']
)

def setup_monitoring():
    """Configura métricas básicas do Prometheus"""
    try:
        # Verificar se porta já está em uso
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 8001))
        if result == 0:
            logger.error("Porta 8001 já está em uso")
            return
        sock.close()
        
        # Iniciar servidor HTTP do Prometheus na porta 8001
        start_http_server(8001)
        logger.info("Métricas Prometheus iniciadas na porta 8001")
    except Exception as e:
        logger.error(f"Erro ao iniciar métricas Prometheus: {e}")
        raise 

async def monitor_thread_usage():
    """Monitora uso de threads"""
    limiter = current_default_thread_limiter()
    threads_in_use = limiter.borrowed_tokens
    
    while True:
        if threads_in_use != limiter.borrowed_tokens:
            logger.info(f"Threads em uso: {limiter.borrowed_tokens}")
            threads_in_use = limiter.borrowed_tokens
        await asyncio.sleep(1)

# Iniciar no startup:
# asyncio.create_task(monitor_thread_usage()) 