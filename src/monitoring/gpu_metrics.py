GPU_UTILIZATION = Gauge(
    'gpu_utilization_percent',
    'Utilização da GPU em porcentagem',
    ['gpu_id', 'gpu_name']
)

GPU_MEMORY = Gauge(
    'gpu_memory_usage_bytes',
    'Uso de memória da GPU',
    ['gpu_id', 'gpu_name']
)

async def collect_gpu_metrics():
    while True:
        for gpu in get_gpu_info():  # Implementar com nvidia-smi
            GPU_UTILIZATION.labels(
                gpu.id, gpu.name
            ).set(gpu.utilization)
            
            GPU_MEMORY.labels(
                gpu.id, gpu.name
            ).set(gpu.used_memory)
            
        await asyncio.sleep(15) 