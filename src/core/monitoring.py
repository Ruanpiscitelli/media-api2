"""Monitoramento básico"""
from prometheus_client import start_http_server, Counter, Gauge, Histogram
import logging
import socket

logger = logging.getLogger(__name__)

# Métricas básicas
REQUESTS = Counter('requests_total', 'Total de requisições')
ERRORS = Counter('errors_total', 'Total de erros')
GPU_MEMORY = Gauge('gpu_memory_mb', 'Memória GPU em MB')

# Adicionar métrica de latência usando Histogram
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'Latência das requisições HTTP',
    ['path', 'method', 'status']
)

def setup_monitoring():
    """Inicia métricas"""
    try:
        # Verificar se porta já está em uso
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 8001))
        if result == 0:
            logger.error("Porta 8001 já está em uso")
            return
        sock.close()
        
        # Iniciar servidor HTTP do Prometheus
        start_http_server(8001)
        logger.info("Métricas iniciadas na porta 8001")
    except Exception as e:
        logger.error(f"Erro ao iniciar métricas: {e}")
        raise 