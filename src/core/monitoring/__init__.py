"""
Sistema de monitoramento centralizado
"""
from prometheus_client import start_http_server
import logging
from .metrics import (
    CACHE_METRICS,
    GPU_METRICS,
    HTTP_METRICS,
    TASK_METRICS
)

logger = logging.getLogger(__name__)

# Exporta métricas para uso em outros módulos
REQUESTS = HTTP_METRICS['requests']
ERRORS = HTTP_METRICS['errors']
REQUEST_LATENCY = HTTP_METRICS['latency']

def setup_monitoring(port: int = 8001):
    """
    Inicia servidor de métricas Prometheus
    
    Args:
        port: Porta para expor métricas (default: 8001)
    """
    try:
        start_http_server(port)
        logger.info(f"✅ Servidor de métricas iniciado na porta {port}")
    except OSError as e:
        if "Address already in use" in str(e):
            logger.warning(f"Porta {port} já em uso, tentando próxima...")
            setup_monitoring(port + 1)
        else:
            logger.error(f"❌ Erro ao iniciar métricas: {e}")
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar métricas: {e}")

__all__ = [
    'CACHE_METRICS',
    'GPU_METRICS',
    'HTTP_METRICS',
    'TASK_METRICS',
    'REQUESTS',
    'ERRORS',
    'REQUEST_LATENCY',
    'setup_monitoring'
]

"""
Métricas Prometheus para monitoramento da API
"""
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging

logger = logging.getLogger(__name__)

# Métricas de requisições
REQUESTS = Counter(
    'http_requests_total',
    'Total de requisições HTTP',
    ['method', 'endpoint', 'status']
)

# Métricas de erros
ERRORS = Counter(
    'http_errors_total',
    'Total de erros HTTP',
    ['method', 'endpoint', 'status']
)

# Latência das requisições
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'Latência das requisições HTTP',
    ['method', 'endpoint']
)

# Métricas de recursos
MEMORY_USAGE = Gauge(
    'memory_usage_bytes',
    'Uso de memória em bytes'
)

CPU_USAGE = Gauge(
    'cpu_usage_percent',
    'Uso de CPU em porcentagem'
)

# Métricas de GPU
GPU_MEMORY_USAGE = Gauge(
    'gpu_memory_usage_bytes',
    'Uso de memória GPU em bytes',
    ['device']
)

GPU_UTILIZATION = Gauge(
    'gpu_utilization_percent',
    'Utilização da GPU em porcentagem',
    ['device']
)

# Métricas de processamento
TASKS_IN_PROGRESS = Gauge(
    'tasks_in_progress',
    'Número de tarefas em processamento'
)

TASKS_COMPLETED = Counter(
    'tasks_completed_total',
    'Total de tarefas completadas',
    ['status']
)

# Métricas de cache
CACHE_HITS = Counter(
    'cache_hits_total',
    'Total de hits no cache'
)

CACHE_MISSES = Counter(
    'cache_misses_total',
    'Total de misses no cache'
)

def setup_monitoring():
    """Inicia métricas na porta 8001"""
    try:
        start_http_server(8001)
        logger.info("✅ Métricas OK")
    except Exception as e:
        logger.error(f"❌ Métricas erro: {e}") 