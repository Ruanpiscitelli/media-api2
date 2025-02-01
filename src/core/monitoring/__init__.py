"""Monitoramento básico"""
from prometheus_client import Counter, Gauge, start_http_server
import logging

logger = logging.getLogger(__name__)

# Métricas mínimas
REQUESTS = Counter('requests_total', 'Total de requisições')
ERRORS = Counter('errors_total', 'Total de erros')
GPU_MEMORY = Gauge('gpu_memory_mb', 'Memória GPU em MB')

def setup_monitoring():
    """Inicia métricas na porta 8001"""
    try:
        start_http_server(8001)
        logger.info("✅ Métricas OK")
    except Exception as e:
        logger.error(f"❌ Métricas erro: {e}") 