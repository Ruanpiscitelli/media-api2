from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from prometheus_client import start_http_server, REGISTRY, Counter, Histogram, Gauge
import logging
from typing import Dict, Any
import psutil
import torch

logger = logging.getLogger(__name__)

def init_tracing():
    """Configura tracing distribuído com OpenTelemetry"""
    resource = Resource(attributes={
        "service.name": "media-api",
        "service.version": "2.0"
    })
    
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    
    # Exportador para Jaeger
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger",
        agent_port=6831,
    )
    
    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

def init_metrics():
    start_http_server(8001)
    REGISTRY.register(gpu_manager.metrics)

# Métricas Prometheus
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total de requisições HTTP",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Latência das requisições HTTP",
    ["method", "endpoint"]
)

GPU_MEMORY = Gauge(
    "gpu_memory_usage_bytes",
    "Uso de memória GPU",
    ["device", "type"]
)

def setup_monitoring():
    """Configura sistema de monitoramento"""
    try:
        # Configurar métricas de GPU
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                GPU_MEMORY.labels(device=i, type="total").set(
                    torch.cuda.get_device_properties(i).total_memory
                )
                
        logger.info("Monitoramento configurado com sucesso")
        
    except Exception as e:
        logger.error(f"Erro configurando monitoramento: {e}")
        raise

async def collect_metrics() -> Dict[str, Any]:
    """Coleta métricas do sistema"""
    metrics = {
        "system": {
            "cpu": psutil.cpu_percent(),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage("/").percent
        }
    }
    
    # Métricas de GPU
    if torch.cuda.is_available():
        metrics["gpu"] = {}
        for i in range(torch.cuda.device_count()):
            metrics["gpu"][i] = {
                "memory": {
                    "used": torch.cuda.memory_allocated(i),
                    "total": torch.cuda.get_device_properties(i).total_memory
                }
            }
            
    return metrics 