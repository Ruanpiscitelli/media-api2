"""
Gerenciador de filas com suporte a priorização e métricas.
Integrado com sistema de distribuição de carga multi-GPU.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from prometheus_client import Counter, Gauge, Histogram

from src.config.gpu_config import get_pipeline_config
from src.core.gpu.scheduler import GPUScheduler, Task

# Configuração de logging
logger = logging.getLogger(__name__)

# Métricas Prometheus
QUEUE_SIZE = Gauge('task_queue_size', 'Number of tasks in queue', ['priority'])
QUEUE_WAIT_TIME = Histogram(
    'task_queue_wait_seconds',
    'Time spent waiting in queue',
    ['priority'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600)
)
TASK_THROUGHPUT = Counter(
    'task_throughput_total',
    'Total number of tasks processed',
    ['type', 'priority']
)

class QueueManager:
    """
    Gerenciador de filas com suporte a múltiplas filas e priorização.
    """
    
    def __init__(self, scheduler: GPUScheduler):
        """
        Inicializa o gerenciador de filas.
        
        Args:
            scheduler: Scheduler de GPUs para execução das tarefas
        """
        self.scheduler = scheduler
        self.config = get_pipeline_config()
        
        # Estado interno
        self.tasks: Dict[UUID, Task] = {}
        self.task_queues: Dict[str, asyncio.Queue] = {
            'realtime': asyncio.Queue(maxsize=100),    # Tarefas que precisam de resposta imediata
            'high': asyncio.Queue(maxsize=200),        # Tarefas importantes
            'normal': asyncio.Queue(maxsize=500),      # Tarefas padrão
            'batch': asyncio.Queue(maxsize=1000)       # Processamento em lote
        }
        
        # Mapeamento de prioridade string -> int
        self.priority_map = {
            'realtime': 0,
            'high': 1,
            'normal': 2,
            'batch': 3
        }
        
        # Inicia workers
        self._start_workers()
        
    def _start_workers(self):
        """
        Inicia workers para processar cada fila.
        """
        for queue_name in self.task_queues:
            for _ in range(self.config['workers_per_queue']):
                asyncio.create_task(
                    self._queue_worker(queue_name)
                )
    
    async def _queue_worker(self, queue_name: str):
        """
        Worker que processa tarefas de uma fila.
        
        Args:
            queue_name: Nome da fila a ser processada
        """
        queue = self.task_queues[queue_name]
        priority = self.priority_map[queue_name]
        
        while True:
            task_id = await queue.get()
            
            try:
                task = self.tasks[task_id]
                
                # Registra tempo de espera
                wait_time = (datetime.now() - task.created_at).total_seconds()
                QUEUE_WAIT_TIME.labels(priority=queue_name).observe(wait_time)
                
                # Submete para o scheduler
                await self.scheduler.submit_task(task)
                
                # Aguarda conclusão
                await self.scheduler.wait_task(task.id)
                
                # Atualiza métricas
                TASK_THROUGHPUT.labels(
                    type=task.type,
                    priority=queue_name
                ).inc()
                
            except Exception as e:
                logger.error(f"Erro processando tarefa {task_id}: {e}")
                
            finally:
                queue.task_done()
                QUEUE_SIZE.labels(priority=queue_name).dec()
    
    async def enqueue_task(
        self,
        task_type: str,
        memory_required: int,
        priority: str = 'normal',
        estimated_duration: Optional[float] = None
    ) -> UUID:
        """
        Adiciona uma nova tarefa à fila.
        
        Args:
            task_type: Tipo da tarefa ('image', 'speech', 'video')
            memory_required: Memória necessária em MB
            priority: Prioridade da tarefa
            estimated_duration: Duração estimada em segundos
            
        Returns:
            ID da tarefa
        """
        # Valida prioridade
        if priority not in self.priority_map:
            raise ValueError(f"Prioridade inválida: {priority}")
            
        # Cria tarefa
        task = Task(
            id=uuid4(),
            type=task_type,
            priority=self.priority_map[priority],
            memory_required=memory_required,
            created_at=datetime.now(),
            estimated_duration=estimated_duration
        )
        
        # Registra tarefa
        self.tasks[task.id] = task
        
        # Adiciona à fila
        await self.task_queues[priority].put(task.id)
        QUEUE_SIZE.labels(priority=priority).inc()
        
        logger.info(
            f"Tarefa {task.id} ({task_type}) adicionada à fila {priority}"
        )
        return task.id
    
    async def get_task_status(self, task_id: UUID) -> Dict:
        """
        Retorna status de uma tarefa.
        
        Args:
            task_id: ID da tarefa
            
        Returns:
            Dicionário com status da tarefa
        """
        if task_id not in self.tasks:
            return {'status': 'not_found'}
            
        task = self.tasks[task_id]
        
        # Calcula tempo de espera
        wait_time = (datetime.now() - task.created_at).total_seconds()
        
        return {
            'status': 'running' if task.started_at else 'queued',
            'type': task.type,
            'priority': task.priority,
            'wait_time': wait_time,
            'gpu_id': task.gpu_id,
            'started_at': task.started_at.isoformat() if task.started_at else None
        }
    
    async def cancel_task(self, task_id: UUID) -> bool:
        """
        Cancela uma tarefa.
        
        Args:
            task_id: ID da tarefa
            
        Returns:
            True se a tarefa foi cancelada, False se não encontrada
        """
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        
        # Remove da fila se ainda não iniciou
        if not task.started_at:
            # Encontra fila correta
            for queue_name, priority in self.priority_map.items():
                if priority == task.priority:
                    queue = self.task_queues[queue_name]
                    # Remove da fila
                    queue._queue.remove(task.id)
                    QUEUE_SIZE.labels(priority=queue_name).dec()
                    break
        
        # Cancela no scheduler se já iniciou
        else:
            await self.scheduler.cancel_task(task_id)
        
        # Remove do registro
        self.tasks.pop(task_id)
        
        logger.info(f"Tarefa {task_id} cancelada")
        return True
    
    async def get_queue_status(self) -> Dict:
        """
        Retorna status de todas as filas.
        
        Returns:
            Dicionário com status das filas
        """
        status = {}
        
        for queue_name, queue in self.task_queues.items():
            status[queue_name] = {
                'size': queue.qsize(),
                'tasks': len([
                    task for task in self.tasks.values()
                    if task.priority == self.priority_map[queue_name]
                    and not task.started_at
                ])
            }
        
        return status

# Instância global do gerenciador
queue_manager = QueueManager(scheduler=None)  # Scheduler será definido na inicialização 