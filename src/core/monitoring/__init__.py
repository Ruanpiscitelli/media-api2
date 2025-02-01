from prometheus_client import Counter, Histogram, start_http_server
import logging

logger = logging.getLogger(__name__)

# Métricas básicas
REQUEST_COUNT = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'api_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

async def setup_monitoring(port: int = 9090):
    """
    Configura o servidor de métricas Prometheus
    
    Args:
        port: Porta para expor as métricas (default: 9090)
    """
    try:
        start_http_server(port)
        logger.info(f"Servidor de métricas Prometheus iniciado na porta {port}")
    except Exception as e:
        logger.error(f"Erro ao iniciar servidor de métricas: {e}")
        raise 