from celery import Celery
from redis import Redis

app = Celery('tasks', broker='redis://localhost:6379/0')

class PriorityQueue:
    """Fila de tarefas com prioridade e preempção"""
    
    def __init__(self):
        self.redis = Redis()
        self.active_tasks = {}

    async def add_task(self, task, priority=1):
        """Adiciona tarefa à fila com prioridade"""
        if not gpu_manager.has_available_gpu(task.vram_required):
            raise ResourceWarning("Nenhuma GPU disponível para a tarefa")
        await self.redis.zadd('tasks', {task.id: priority})

    async def preempt_task(self, task_id):
        """Interrompe tarefa em execução para prioridade maior"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel() 