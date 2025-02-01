"""
Métricas Prometheus centralizadas
"""
from prometheus_client import Counter, Histogram, Gauge

# Cache Metrics
CACHE_METRICS = {
    'hits': Counter(
        'cache_hits',  # Removido _total para evitar duplicação
        'Total de cache hits',
        ['namespace']
    ),
    'misses': Counter(
        'cache_misses',
        'Total de cache misses',
        ['namespace']
    ),
    'latency': Histogram(
        'cache_operation_duration_seconds',
        'Latência das operações de cache',
        ['operation']
    )
}

# GPU Metrics
GPU_METRICS = {
    'memory': Gauge(
        'gpu_memory_bytes',
        'Uso de memória GPU em bytes',
        ['device']
    ),
    'utilization': Gauge(
        'gpu_utilization_percent',
        'Utilização da GPU em porcentagem',
        ['device']
    ),
    'temperature': Gauge(
        'gpu_temperature_celsius',
        'Temperatura da GPU em Celsius',
        ['device']
    ),
    'power': Gauge(
        'gpu_power_watts',
        'Consumo de energia da GPU em watts',
        ['device']
    ),
    'errors': Counter(
        'gpu_errors',
        'Erros da GPU',
        ['device', 'type']
    )
}

# HTTP Metrics
HTTP_METRICS = {
    'requests': Counter(
        'http_requests',
        'Total de requisições HTTP',
        ['method', 'endpoint', 'status']
    ),
    'latency': Histogram(
        'http_request_duration_seconds',
        'Latência das requisições HTTP',
        ['method', 'endpoint']
    ),
    'errors': Counter(
        'http_errors',
        'Total de erros HTTP',
        ['method', 'endpoint', 'error']
    )
}

# Task Metrics
TASK_METRICS = {
    'queued': Gauge(
        'tasks_queued',
        'Tarefas na fila'
    ),
    'processing': Gauge(
        'tasks_processing',
        'Tarefas em processamento'
    ),
    'completed': Counter(
        'tasks_completed',
        'Total de tarefas completadas',
        ['status']
    ),
    'duration': Histogram(
        'task_duration_seconds',
        'Duração das tarefas',
        ['type']
    )
} 