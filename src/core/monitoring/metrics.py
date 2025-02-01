"""
Métricas Prometheus centralizadas
"""
from prometheus_client import Counter, Gauge, Histogram
from typing import Dict

# GPU Metrics
GPU_METRICS: Dict[str, Gauge] = {
    'utilization': Gauge('gpu_utilization', 'Utilização da GPU', ['gpu_id']),
    'memory_used': Gauge('gpu_memory_used', 'VRAM utilizada', ['gpu_id']),
    'temperature': Gauge('gpu_temperature', 'Temperatura da GPU', ['gpu_id']),
    'task_count': Gauge('gpu_task_count', 'Número de tarefas na GPU', ['gpu_id']),
    'nvlink_speed': Gauge('gpu_nvlink_speed', 'Velocidade NVLink', ['gpu_id', 'peer_id']),
    'errors': Counter('gpu_errors_total', 'Total de erros da GPU', ['gpu_id'])
}

# Cache Metrics
CACHE_METRICS: Dict[str, Counter] = {
    'hits': Counter('cache_hits_total', 'Total de cache hits', ['namespace']),
    'misses': Counter('cache_misses_total', 'Total de cache misses', ['namespace']),
    'errors': Counter('cache_errors_total', 'Total de erros de cache', ['namespace'])
}

# API Metrics
API_METRICS = {
    'gpu_temperature': Gauge(
        'gpu_temperature',
        'GPU temperature in celsius',
        ['device_id']
    ),
    'gpu_utilization': Gauge(
        'gpu_utilization',
        'GPU utilization percentage',
        ['device_id']
    ),
    'gpu_memory_used': Gauge(
        'gpu_memory_used',
        'GPU memory usage in bytes',
        ['device_id']
    ),
    'task_duration': Histogram(
        'task_duration_seconds',
        'Task processing duration in seconds',
        ['task_type']
    ),
    'tasks_queued': Gauge(
        'tasks_queued',
        'Number of tasks currently in queue',
        ['task_type']
    )
} 