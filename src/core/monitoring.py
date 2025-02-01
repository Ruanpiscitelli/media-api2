"""
Configuração de monitoramento usando Prometheus
"""
from prometheus_client import Counter, Histogram, start_http_server
import logging

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
        # Iniciar servidor HTTP do Prometheus na porta 8001
        start_http_server(8001)
        logger.info("Métricas Prometheus iniciadas na porta 8001")
    except Exception as e:
        logger.error(f"Erro ao iniciar métricas Prometheus: {e}")
        raise 