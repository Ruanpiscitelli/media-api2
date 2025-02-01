from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from prometheus_client import start_http_server, REGISTRY

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