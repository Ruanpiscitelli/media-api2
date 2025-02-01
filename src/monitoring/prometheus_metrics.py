from prometheus_client import Gauge

GPU_METRICS = {
    'vram_usage': Gauge('gpu_vram_usage', 'VRAM usage in MB', ['gpu_id']),
    'utilization': Gauge('gpu_utilization', 'GPU utilization %', ['gpu_id']),
    'temperature': Gauge('gpu_temperature', 'GPU temperature in C', ['gpu_id'])
}

async def update_gpu_metrics():
    while True:
        for gpu in get_gpu_status():  # Implementar com nvidia-smi
            GPU_METRICS['vram_usage'].labels(gpu['id']).set(gpu['used_vram'])
            GPU_METRICS['utilization'].labels(gpu['id']).set(gpu['utilization'])
            GPU_METRICS['temperature'].labels(gpu['id']).set(gpu['temperature'])
        await asyncio.sleep(15) 