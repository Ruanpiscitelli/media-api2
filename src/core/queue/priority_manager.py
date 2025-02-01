import asyncio
import os
import signal

class PriorityQueue:
    def __init__(self):
        self.queues = {
            "realtime": asyncio.Queue(maxsize=10),
            "high": asyncio.Queue(maxsize=100),
            "normal": asyncio.Queue(maxsize=1000),
            "low": asyncio.Queue(maxsize=5000)
        }
    
    async def add_task(self, task, priority="normal"):
        if priority not in self.queues:
            raise InvalidPriorityError()
        
        await self.queues[priority].put(task)
    
    async def get_next_task(self):
        for queue in ["realtime", "high", "normal", "low"]:
            if not self.queues[queue].empty():
                return await self.queues[queue].get()
        return None 

    async def preempt_task(self, gpu_id: int):
        """Interrompe tarefa de menor prioridade na GPU"""
        current_tasks = self.gpu_manager.get_gpu_tasks(gpu_id)
        if not current_tasks:
            return
            
        # Encontrar tarefa com menor prioridade
        lowest_priority = min(current_tasks, key=lambda x: x['priority'])
        
        # Interromper processo
        os.kill(lowest_priority['pid'], signal.SIGSTOP)
        
        # Reenfileirar tarefa
        await self.add_task(lowest_priority)