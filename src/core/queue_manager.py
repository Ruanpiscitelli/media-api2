"""
Gerenciador de fila de tarefas.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger(__name__)

@dataclass
class QueueTask:
    """Representa uma tarefa na fila"""
    task_id: str
    type: str
    params: Dict[str, Any]
    priority: int = 0
    created_at: datetime = datetime.now()
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class QueueManager:
    """Gerenciador de fila de tarefas"""
    
    def __init__(self):
        self.tasks: Dict[str, QueueTask] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.lock = asyncio.Lock()
        
    async def add_task(self, task_id: str, task_type: str, params: Dict[str, Any], priority: int = 0) -> QueueTask:
        """Adiciona uma tarefa à fila"""
        task = QueueTask(
            task_id=task_id,
            type=task_type,
            params=params,
            priority=priority
        )
        
        async with self.lock:
            self.tasks[task_id] = task
            await self.queue.put((priority, task))
            
        logger.info(f"Tarefa {task_id} adicionada à fila")
        return task
        
    async def get_next_task(self) -> Optional[QueueTask]:
        """Obtém próxima tarefa da fila"""
        try:
            _, task = await self.queue.get()
            task.started_at = datetime.now()
            task.status = "processing"
            return task
        except asyncio.QueueEmpty:
            return None
            
    async def complete_task(self, task_id: str, result: Dict[str, Any]):
        """Marca tarefa como concluída"""
        async with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.completed_at = datetime.now()
                task.status = "completed"
                task.result = result
                
    async def fail_task(self, task_id: str, error: str):
        """Marca tarefa como falha"""
        async with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.completed_at = datetime.now()
                task.status = "failed"
                task.error = error
                
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Obtém status de uma tarefa"""
        if task_id not in self.tasks:
            return None
            
        task = self.tasks[task_id]
        return {
            "task_id": task.task_id,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result": task.result,
            "error": task.error
        }
        
    async def clean_completed_tasks(self, max_age_hours: int = 24):
        """Limpa tarefas antigas concluídas"""
        async with self.lock:
            now = datetime.now()
            to_remove = []
            
            for task_id, task in self.tasks.items():
                if task.completed_at:
                    age = (now - task.completed_at).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(task_id)
                        
            for task_id in to_remove:
                del self.tasks[task_id]

# Instância global do gerenciador
queue_manager = QueueManager() 