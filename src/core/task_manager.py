"""
Gerenciador de tarefas com suporte a priorização e distribuição em GPUs.
Implementa fila de prioridade e alocação dinâmica de recursos.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from uuid import UUID, uuid4
from prometheus_client import Counter, Gauge, Histogram
import psutil

from src.core.gpu.manager import GPUManager
from src.core.config import settings

# Configuração de logging
logger = logging.getLogger(__name__)

# Métricas Prometheus
TASK_METRICS = {
    'queue_size': Gauge('task_queue_size', 'Tasks in queue', ['priority']),
    'wait_time': Histogram('task_wait_seconds', 'Queue wait time', ['priority']),
    'throughput': Counter('task_throughput_total', 'Tasks processed', ['type']),
    'errors': Counter('task_errors_total', 'Task errors', ['type', 'error']),
    'gpu_memory': Gauge('gpu_memory_bytes', 'GPU memory usage', ['gpu_id'])
}

# Configurações
TASK_CONFIGS = {
    'memory_limits': {
        'image': 12 * 1024,  # 12GB
        'speech': 6 * 1024,  # 6GB
        'video': 16 * 1024   # 16GB
    },
    'timeouts': {
        'task_execution': 3600,  # 1 hora
        'queue_add': 5,         # 5 segundos
        'cleanup_interval': 300  # 5 minutos
    },
    'queue_sizes': {
        'realtime': 100,
        'high': 200,
        'normal': 500,
        'batch': 1000
    },
    'priorities': {
        'realtime': 0,
        'high': 1, 
        'normal': 2,
        'batch': 3
    }
}

@dataclass
class Task:
    """Representa uma tarefa de processamento"""
    id: UUID
    type: str                # 'image', 'speech', 'video'
    priority: int            # 0 (mais alta) a 3 (mais baixa)
    memory_required: int     # MB necessários
    created_at: datetime
    gpu_id: Optional[int] = None
    started_at: Optional[datetime] = None
    estimated_duration: Optional[float] = None
    error: Optional[str] = None

class TaskError(Exception):
    """Exceção base para erros de tarefa"""
    pass

class TaskManager:
    """
    Gerenciador unificado de tarefas com suporte a priorização e GPUs.
    Combina gerenciamento de fila e alocação de recursos.
    """
    
    def __init__(self, gpu_manager: GPUManager):
        """
        Inicializa o gerenciador.
        
        Args:
            gpu_manager: Gerenciador de GPUs
        """
        self.gpu_manager = gpu_manager
        
        # Estado interno
        self.tasks: Dict[UUID, Task] = {}
        self.queues = {
            name: asyncio.Queue(maxsize=size)
            for name, size in TASK_CONFIGS['queue_sizes'].items()
        }
        self.active_tasks: Dict[UUID, Task] = {}
        self.cancelled_tasks: Set[UUID] = set()
        self.task_events: Dict[UUID, asyncio.Event] = {}
        
        # Lock para operações críticas
        self._lock = asyncio.Lock()
        
        # Inicia workers e cleanup
        self._start_workers()
        self._start_cleanup()
        
        self.max_tasks = settings.MAX_CONCURRENT_TASKS
        self.current_tasks = 0
        
        self._task_locks = {}  # Locks por tarefa
        
    def _start_workers(self):
        """Inicia workers para cada fila"""
        for queue_name in self.queues:
            for _ in range(self._get_worker_count(queue_name)):
                asyncio.create_task(self._queue_worker(queue_name))
                
    def _start_cleanup(self):
        """Inicia tarefa de limpeza periódica"""
        asyncio.create_task(self._cleanup_loop())
        
    def _get_worker_count(self, queue_name: str) -> int:
        """Retorna número de workers para uma fila"""
        return {
            'realtime': 4,
            'high': 3,
            'normal': 2,
            'batch': 1
        }.get(queue_name, 1)
        
    async def _cleanup_loop(self):
        """Remove tarefas órfãs e libera recursos"""
        while True:
            try:
                async with self._lock:
                    now = datetime.now()
                    
                    # Remove tarefas antigas
                    for task_id, task in list(self.tasks.items()):
                        if self._should_cleanup_task(task, now):
                            await self._cancel_task_internal(task_id)
                            
                    # Remove eventos órfãos
                    for task_id in list(self.task_events.keys()):
                        if task_id not in self.active_tasks:
                            self.task_events.pop(task_id)
                            
            except Exception as e:
                logger.error(f"Erro na limpeza: {e}")
                
            await asyncio.sleep(TASK_CONFIGS['timeouts']['cleanup_interval'])
            
    def _should_cleanup_task(self, task: Task, now: datetime) -> bool:
        """Verifica se uma tarefa deve ser limpa"""
        if task.started_at:
            duration = (now - task.started_at).total_seconds()
            return duration > TASK_CONFIGS['timeouts']['task_execution']
        else:
            wait_time = (now - task.created_at).total_seconds()
            return wait_time > TASK_CONFIGS['timeouts']['task_execution']
    
    async def _queue_worker(self, queue_name: str):
        """Processa tarefas de uma fila"""
        queue = self.queues[queue_name]
        
        while True:
            task_id = await queue.get()
            start_time = None
            
            try:
                if task_id in self.cancelled_tasks:
                    self.cancelled_tasks.remove(task_id)
                    continue
                    
                task = self.tasks[task_id]
                
                # Registra métricas de espera
                wait_time = (datetime.now() - task.created_at).total_seconds()
                TASK_METRICS['wait_time'].labels(priority=queue_name).observe(wait_time)
                
                # Aloca GPU e processa
                gpu_id = await self._allocate_gpu(task)
                if gpu_id is not None:
                    await self._process_task(task, gpu_id)
                else:
                    # Recoloca na fila se não conseguiu GPU
                    await queue.put(task_id)
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Erro processando tarefa {task_id}: {e}")
                TASK_METRICS['errors'].labels(
                    type=task.type,
                    error='processing'
                ).inc()
                
            finally:
                queue.task_done()
                TASK_METRICS['queue_size'].labels(priority=queue_name).dec()
                
    async def _allocate_gpu(self, task: Task) -> Optional[int]:
        """Aloca GPU para uma tarefa"""
        try:
            return await self.gpu_manager.allocate_gpu(
                task.type,
                task.memory_required
            )
        except Exception as e:
            logger.error(f"Erro alocando GPU: {e}")
            TASK_METRICS['errors'].labels(
                type=task.type,
                error='gpu_allocation'
            ).inc()
            return None
            
    async def _process_task(self, task: Task, gpu_id: int):
        """Processa uma tarefa em uma GPU"""
        async with self._lock:
            task.gpu_id = gpu_id
            task.started_at = datetime.now()
            self.active_tasks[task.id] = task
            self.current_tasks += 1  # Incrementa contador ao iniciar tarefa
            TASK_METRICS['gpu_memory'].labels(gpu_id=gpu_id).inc(task.memory_required)
            
            if task.id in self.task_events:
                self.task_events[task.id].set()
                
        try:
            # Simula processamento
            if task.estimated_duration:
                await asyncio.sleep(task.estimated_duration)
                
            # Cleanup
            await self._cleanup_task(task)
            TASK_METRICS['throughput'].labels(type=task.type).inc()
            
        except Exception as e:
            logger.error(f"Erro executando tarefa {task.id}: {e}")
            task.error = str(e)
            TASK_METRICS['errors'].labels(
                type=task.type,
                error='execution'
            ).inc()
            await self._cancel_task_internal(task.id)
            
    async def _cleanup_task(self, task: Task):
        """Limpa recursos de uma tarefa"""
        async with self._lock:
            self.active_tasks.pop(task.id, None)
            self.current_tasks -= 1  # Decrementa contador ao finalizar tarefa
            if task.gpu_id is not None:
                TASK_METRICS['gpu_memory'].labels(gpu_id=task.gpu_id).dec(task.memory_required)
                await self.gpu_manager.release_gpu(task.gpu_id)
                
            if task.id in self.task_events:
                self.task_events[task.id].set()
                self.task_events.pop(task.id)
                
    async def _cancel_task_internal(self, task_id: UUID):
        """Cancela uma tarefa internamente"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            await self._cleanup_task(task)
            
        self.tasks.pop(task_id, None)
        self.cancelled_tasks.discard(task_id)
        
    # API Pública
    
    async def submit_task(
        self,
        task_type: str,
        memory_required: int,
        priority: str = 'normal',
        estimated_duration: Optional[float] = None
    ) -> UUID:
        """Submete uma nova tarefa"""
        # Validações
        if task_type not in TASK_CONFIGS['memory_limits']:
            raise TaskError(f"Tipo de tarefa inválido: {task_type}")
            
        if priority not in TASK_CONFIGS['priorities']:
            raise TaskError(f"Prioridade inválida: {priority}")
            
        if memory_required <= 0:
            raise TaskError("Memória requerida deve ser maior que 0")
            
        if memory_required > TASK_CONFIGS['memory_limits'][task_type]:
            raise TaskError(f"Memória excede limite para {task_type}")
            
        # Cria tarefa
        task = Task(
            id=uuid4(),
            type=task_type,
            priority=TASK_CONFIGS['priorities'][priority],
            memory_required=memory_required,
            created_at=datetime.now(),
            estimated_duration=estimated_duration
        )
        
        async with self._lock:
            # Registra tarefa
            self.tasks[task.id] = task
            self.task_events[task.id] = asyncio.Event()
            
            try:
                # Verificar limites globais
                if len(self.tasks) >= settings.MAX_CONCURRENT_TASKS:
                    raise TaskError("Limite de tarefas concorrentes atingido")
                    
                # Verificar recursos antes de aceitar
                if not await self.can_accept_task():
                    raise TaskError("Sistema sobrecarregado")
                
                # Adiciona à fila
                await asyncio.wait_for(
                    self.queues[priority].put(task.id),
                    timeout=TASK_CONFIGS['timeouts']['queue_add']
                )
                TASK_METRICS['queue_size'].labels(priority=priority).inc()
                
            except asyncio.TimeoutError:
                self.tasks.pop(task.id)
                self.task_events.pop(task.id)
                TASK_METRICS['errors'].labels(
                    type=task_type,
                    error='queue_full'
                ).inc()
                raise TaskError(f"Fila {priority} está cheia")
                
        logger.info(f"Tarefa {task.id} ({task_type}) adicionada à fila {priority}")
        return task.id
        
    async def get_task_status(self, task_id: UUID) -> Dict:
        """Retorna status de uma tarefa"""
        if task_id not in self.tasks:
            return {'status': 'not_found'}
            
        task = self.tasks[task_id]
        wait_time = (datetime.now() - task.created_at).total_seconds()
        
        status = 'cancelled' if task_id in self.cancelled_tasks else (
            'running' if task.started_at else 'queued'
        )
        
        return {
            'status': status,
            'type': task.type,
            'priority': task.priority,
            'wait_time': wait_time,
            'gpu_id': task.gpu_id,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'estimated_completion': (
                (task.started_at + timedelta(seconds=task.estimated_duration)).isoformat()
                if task.started_at and task.estimated_duration
                else None
            ),
            'error': task.error
        }
        
    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancela uma tarefa"""
        async with self._lock:
            if task_id not in self.tasks:
                return False
                
            await self._cancel_task_internal(task_id)
            logger.info(f"Tarefa {task_id} cancelada")
            return True
            
    async def get_queue_status(self) -> Dict:
        """Retorna status das filas"""
        async with self._lock:
            return {
                name: {
                    'size': queue.qsize(),
                    'active': len([
                        t for t in self.active_tasks.values()
                        if t.priority == TASK_CONFIGS['priorities'][name]
                    ]),
                    'waiting': len([
                        t for t in self.tasks.values()
                        if t.priority == TASK_CONFIGS['priorities'][name]
                        and not t.started_at
                    ]),
                    'errors': len([
                        t for t in self.tasks.values()
                        if t.priority == TASK_CONFIGS['priorities'][name]
                        and t.error is not None
                    ])
                }
                for name, queue in self.queues.items()
            }

    async def can_accept_task(self) -> bool:
        """Verifica se pode aceitar nova tarefa"""
        async with self._lock:
            if self.current_tasks >= self.max_tasks:
                return False
                
            # Verificar carga do sistema
            cpu_percent = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            
            if cpu_percent > 90 or mem.percent > 90:
                return False
                
            return True

# Instância global
task_manager: Optional[TaskManager] = None 