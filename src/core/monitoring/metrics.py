"""
Métricas Prometheus centralizadas
"""
from prometheus_client import Counter, Histogram, Gauge

# Cache Metrics
CACHE_METRICS = {
    'hits': Counter(
        'api_cache_hits',
        'Total de cache hits',
        ['namespace']
    ),
    'misses': Counter(
        'api_cache_misses',
        'Total de cache misses',
        ['namespace']
    ),
    'latency': Histogram(
        'api_cache_operation_seconds',
        'Latência das operações de cache',
        ['operation']
    )
}

# GPU Metrics
GPU_METRICS = {
    'memory': Gauge(
        'api_gpu_memory_bytes',
        'Uso de memória GPU em bytes',
        ['device']
    ),
    'utilization': Gauge(
        'api_gpu_utilization',
        'Utilização da GPU em porcentagem',
        ['device']
    ),
    'temperature': Gauge(
        'api_gpu_temperature',
        'Temperatura da GPU em Celsius',
        ['device']
    ),
    'power': Gauge(
        'api_gpu_power_watts',
        'Consumo de energia da GPU em watts',
        ['device']
    ),
    'errors': Counter(
        'api_gpu_errors',
        'Erros da GPU',
        ['device', 'type']
    )
}

# HTTP Metrics
HTTP_METRICS = {
    'requests': Counter(
        'api_http_requests',
        'Total de requisições HTTP',
        ['method', 'endpoint', 'status']
    ),
    'latency': Histogram(
        'api_http_duration_seconds',
        'Latência das requisições HTTP',
        ['method', 'endpoint']
    ),
    'errors': Counter(
        'api_http_errors',
        'Total de erros HTTP',
        ['method', 'endpoint', 'error']
    )
}

# Task Metrics
TASK_METRICS = {
    'queued': Gauge(
        'api_tasks_queued',
        'Tarefas na fila'
    ),
    'processing': Gauge(
        'api_tasks_processing',
        'Tarefas em processamento'
    ),
    'completed': Counter(
        'api_tasks_completed',
        'Total de tarefas completadas',
        ['status']
    ),
    'duration': Histogram(
        'api_task_duration_seconds',
        'Duração das tarefas',
        ['type']
    )
} 