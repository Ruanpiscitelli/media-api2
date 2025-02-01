"""
Scheduler de tarefas para GPUs com suporte a priorização e preempção.
Otimizado para workloads de geração de mídia em múltiplas GPUs.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import UUID

from src.config.gpu_config import get_gpu_config, get_pipeline_config
from src.core.gpu.manager import GPUManager

# Configuração de logging
logger = logging.getLogger(__name__)

@dataclass
class Task:
    """
    Representa uma tarefa de processamento em GPU.
    """
    id: UUID
    type: str                # 'image', 'speech', 'video'
    priority: int            # 0 (mais alta) a 3 (mais baixa)
    memory_required: int     # MB necessários
    created_at: datetime
    gpu_id: Optional[int] = None
    started_at: Optional[datetime] = None
    estimated_duration: Optional[float] = None  # segundos

class GPUScheduler:
    """
    Scheduler de tarefas para múltiplas GPUs com suporte a priorização.
    """
    
    def __init__(self, gpu_manager: GPUManager):
        """
        Inicializa o scheduler.
        
        Args:
            gpu_manager: Instância do gerenciador de GPUs
        """
        self.gpu_manager = gpu_manager
        self.config = get_gpu_config()
        self.pipeline_config = get_pipeline_config()
        
        # Filas de tarefas por prioridade
        self.task_queues: Dict[int, asyncio.Queue] = {
            priority: asyncio.Queue(maxsize=self.pipeline_config['queue_size'])
            for priority in self.pipeline_config['priority_levels'].values()
        }
        
        # Estado interno
        self.active_tasks: Dict[UUID, Task] = {}
        self.preempted_tasks: Set[UUID] = set()
        self.task_events: Dict[UUID, asyncio.Event] = {}
        
        # Inicia workers
        self._start_workers()
    
    def _start_workers(self):
        """
        Inicia workers para processamento de filas.
        """
        for priority in self.pipeline_config['priority_levels'].values():
            asyncio.create_task(self._queue_worker(priority))
    
    async def _queue_worker(self, priority: int):
        """
        Worker que processa tarefas de uma fila específica.
        
        Args:
            priority: Nível de prioridade da fila
        """
        queue = self.task_queues[priority]
        
        while True:
            task = await queue.get()
            
            try:
                # Tenta alocar GPU
                gpu_id = await self.gpu_manager.allocate_gpu(
                    task.type,
                    task.memory_required
                )
                
                if gpu_id is not None:
                    # Registra início da tarefa
                    task.gpu_id = gpu_id
                    task.started_at = datetime.now()
                    self.active_tasks[task.id] = task
                    
                    # Notifica que a tarefa pode começar
                    if task.id in self.task_events:
                        self.task_events[task.id].set()
                    
                    # Aguarda conclusão da tarefa
                    await self._wait_task_completion(task)
                    
                else:
                    # Não conseguiu alocar GPU, tenta preempção
                    if await self._try_preemption(task):
                        logger.info(f"Tarefa {task.id} preemptou outra tarefa")
                    else:
                        # Recoloca na fila
                        await queue.put(task)
                        await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Erro processando tarefa {task.id}: {e}")
                
            finally:
                queue.task_done()
    
    async def _try_preemption(self, task: Task) -> bool:
        """
        Tenta fazer preempção de uma tarefa de menor prioridade.
        
        Args:
            task: Tarefa que precisa de GPU
            
        Returns:
            True se conseguiu fazer preempção, False caso contrário
        """
        # Só tenta preempção para tarefas de alta prioridade
        if task.priority > 1:
            return False
            
        # Procura tarefa de menor prioridade
        for active_task in self.active_tasks.values():
            if (active_task.priority > task.priority and 
                active_task.memory_required >= task.memory_required):
                
                # Preempta a tarefa
                await self._preempt_task(active_task)
                
                # Aloca GPU para nova tarefa
                task.gpu_id = active_task.gpu_id
                task.started_at = datetime.now()
                self.active_tasks[task.id] = task
                
                if task.id in self.task_events:
                    self.task_events[task.id].set()
                
                return True
        
        return False
    
    async def _preempt_task(self, task: Task):
        """
        Faz preempção de uma tarefa ativa.
        
        Args:
            task: Tarefa a ser preemptada
        """
        # Remove dos ativos e marca como preemptada
        self.active_tasks.pop(task.id, None)
        self.preempted_tasks.add(task.id)
        
        # Libera GPU
        if task.gpu_id is not None:
            await self.gpu_manager.release_gpu(task.gpu_id)
        
        # Recoloca na fila original
        await self.task_queues[task.priority].put(task)
        
        logger.info(f"Tarefa {task.id} preemptada")
    
    async def _wait_task_completion(self, task: Task):
        """
        Aguarda conclusão de uma tarefa.
        
        Args:
            task: Tarefa a ser monitorada
        """
        # Aguarda pelo tempo estimado
        if task.estimated_duration:
            await asyncio.sleep(task.estimated_duration)
        
        # Cleanup
        self.active_tasks.pop(task.id, None)
        self.preempted_tasks.discard(task.id)
        self.task_events.pop(task.id, None)
        
        # Libera GPU
        if task.gpu_id is not None:
            await self.gpu_manager.release_gpu(task.gpu_id)
    
    async def submit_task(self, task: Task) -> bool:
        """
        Submete uma nova tarefa para processamento.
        
        Args:
            task: Tarefa a ser processada
            
        Returns:
            True se a tarefa foi aceita, False se a fila está cheia
        """
        try:
            # Cria evento para notificação
            self.task_events[task.id] = asyncio.Event()
            
            # Adiciona na fila apropriada
            queue = self.task_queues[task.priority]
            await queue.put(task)
            
            logger.info(f"Tarefa {task.id} submetida com prioridade {task.priority}")
            return True
            
        except asyncio.QueueFull:
            logger.warning(f"Fila cheia para prioridade {task.priority}")
            return False
    
    async def wait_task(self, task_id: UUID, timeout: Optional[float] = None) -> bool:
        """
        Aguarda conclusão de uma tarefa.
        
        Args:
            task_id: ID da tarefa
            timeout: Timeout em segundos
            
        Returns:
            True se a tarefa foi concluída, False se timeout
        """
        if task_id not in self.task_events:
            return False
            
        try:
            return await asyncio.wait_for(
                self.task_events[task_id].wait(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return False
    
    async def cancel_task(self, task_id: UUID) -> bool:
        """
        Cancela uma tarefa em execução ou na fila.
        
        Args:
            task_id: ID da tarefa
            
        Returns:
            True se a tarefa foi cancelada, False se não encontrada
        """
        # Remove da fila se ainda não iniciou
        for queue in self.task_queues.values():
            for task in queue._queue:
                if task.id == task_id:
                    queue._queue.remove(task)
                    logger.info(f"Tarefa {task_id} removida da fila")
                    return True
        
        # Cancela se estiver em execução
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            await self._preempt_task(task)
            logger.info(f"Tarefa {task_id} cancelada durante execução")
            return True
        
        return False
    
    async def get_queue_status(self) -> Dict:
        """
        Retorna status das filas de tarefas.
        
        Returns:
            Dicionário com informações das filas
        """
        return {
            priority: {
                'size': queue.qsize(),
                'active_tasks': len([
                    task for task in self.active_tasks.values()
                    if task.priority == priority
                ])
            }
            for priority, queue in self.task_queues.items()
        }
    
    def estimate_wait_time(self, task: Task) -> float:
        """
        Estima tempo de espera para uma nova tarefa.
        
        Args:
            task: Tarefa a ser estimada
            
        Returns:
            Tempo estimado em segundos
        """
        # Considera apenas tarefas de maior prioridade
        total_wait = 0
        
        for priority in range(task.priority + 1):
            queue = self.task_queues[priority]
            
            # Soma duração estimada das tarefas na fila
            for queued_task in queue._queue:
                if queued_task.estimated_duration:
                    total_wait += queued_task.estimated_duration
            
            # Soma tempo restante das tarefas ativas
            for active_task in self.active_tasks.values():
                if active_task.priority == priority and active_task.started_at:
                    elapsed = (datetime.now() - active_task.started_at).total_seconds()
                    if active_task.estimated_duration:
                        remaining = max(0, active_task.estimated_duration - elapsed)
                        total_wait += remaining
        
        return total_wait 