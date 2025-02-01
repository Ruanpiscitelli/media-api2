import asyncio

class GPUBalancer:
    def __init__(self):
        self.gpus = [
            GPU(0, "RTX 4090", 24*1024),
            GPU(1, "RTX 4090", 24*1024),
            GPU(2, "RTX 4090", 24*1024),
            GPU(3, "RTX 4090", 24*1024)
        ]
        self.lock = asyncio.Lock()

    async def allocate_gpu(self, task: TaskRequest) -> int:
        async with self.lock:
            # Ordenar GPUs por memória livre
            sorted_gpus = sorted(
                self.gpus, 
                key=lambda g: g.free_vram, 
                reverse=True
            )
            
            for gpu in sorted_gpus:
                if gpu.can_handle(task):
                    await gpu.allocate(task)
                    return gpu.id
                    
            raise InsufficientVRAMError("No GPUs available with sufficient VRAM") 