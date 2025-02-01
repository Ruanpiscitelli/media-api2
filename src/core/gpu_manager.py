"""
Gerenciador de recursos GPU.
Controla alocação, monitoramento e liberação de recursos GPU.
"""

import torch
import logging
import asyncio
from typing import Optional, Dict, List
from dataclasses import dataclass
from src.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class GPUTask:
    """Representa uma tarefa usando GPU"""
    task_id: str
    gpu_id: int
    vram_required: int
    priority: int = 0
    start_time: Optional[float] = None

class GPUManager:
    """Gerenciador de recursos GPU"""
    
    def __init__(self):
        """Inicializa o gerenciador GPU"""
        self.available_gpus = []
        self.tasks: Dict[str, GPUTask] = {}
        self.lock = asyncio.Lock()
        self._initialize_gpus()
        
    def _initialize_gpus(self):
        """Inicializa lista de GPUs disponíveis"""
        if not torch.cuda.is_available():
            logger.warning("CUDA não disponível. Usando CPU.")
            return
            
        for gpu_id in range(torch.cuda.device_count()):
            total_memory = torch.cuda.get_device_properties(gpu_id).total_memory
            self.available_gpus.append({
                "id": gpu_id,
                "total_memory": total_memory,
                "used_memory": 0,
                "tasks": []
            })
            logger.info(f"GPU {gpu_id} inicializada: {total_memory/1024**3:.1f}GB VRAM")
    
    async def allocate_gpu(self, task_id: str, vram_required: int, priority: int = 0) -> Optional[int]:
        """
        Aloca uma GPU para uma tarefa.
        
        Args:
            task_id: ID único da tarefa
            vram_required: VRAM necessária em bytes
            priority: Prioridade da tarefa (maior = mais prioritário)
            
        Returns:
            ID da GPU alocada ou None se não houver GPU disponível
        """
        async with self.lock:
            if not self.available_gpus:
                return None
                
            # Encontrar GPU com memória suficiente
            for gpu in self.available_gpus:
                free_memory = gpu["total_memory"] - gpu["used_memory"]
                if free_memory >= vram_required:
                    gpu["used_memory"] += vram_required
                    task = GPUTask(
                        task_id=task_id,
                        gpu_id=gpu["id"],
                        vram_required=vram_required,
                        priority=priority
                    )
                    self.tasks[task_id] = task
                    gpu["tasks"].append(task_id)
                    logger.info(f"GPU {gpu['id']} alocada para tarefa {task_id}")
                    return gpu["id"]
                    
            # Se não encontrou GPU livre, tentar liberar tarefas de menor prioridade
            return await self._try_preempt_gpu(vram_required, priority)
    
    async def _try_preempt_gpu(self, vram_required: int, priority: int) -> Optional[int]:
        """Tenta liberar GPU preemptando tarefas de menor prioridade"""
        for gpu in self.available_gpus:
            preemptable_tasks = [
                self.tasks[t] for t in gpu["tasks"]
                if self.tasks[t].priority < priority
            ]
            
            if not preemptable_tasks:
                continue
                
            # Ordenar por prioridade (menor primeiro)
            preemptable_tasks.sort(key=lambda t: t.priority)
            
            freed_memory = 0
            tasks_to_remove = []
            
            for task in preemptable_tasks:
                freed_memory += task.vram_required
                tasks_to_remove.append(task.task_id)
                if freed_memory >= vram_required:
                    break
                    
            if freed_memory >= vram_required:
                # Remover tarefas preemptadas
                for task_id in tasks_to_remove:
                    await self.release_gpu(task_id)
                return gpu["id"]
                
        return None
    
    async def release_gpu(self, task_id: str):
        """
        Libera recursos GPU de uma tarefa.
        
        Args:
            task_id: ID da tarefa
        """
        async with self.lock:
            if task_id not in self.tasks:
                return
                
            task = self.tasks[task_id]
            for gpu in self.available_gpus:
                if gpu["id"] == task.gpu_id:
                    gpu["used_memory"] -= task.vram_required
                    gpu["tasks"].remove(task_id)
                    break
                    
            del self.tasks[task_id]
            logger.info(f"GPU {task.gpu_id} liberada da tarefa {task_id}")
            
    async def get_gpu_status(self) -> List[Dict]:
        """
        Retorna status atual das GPUs.
        
        Returns:
            Lista com informações de cada GPU
        """
        async with self.lock:
            status = []
            for gpu in self.available_gpus:
                status.append({
                    "id": gpu["id"],
                    "total_memory": gpu["total_memory"],
                    "used_memory": gpu["used_memory"],
                    "free_memory": gpu["total_memory"] - gpu["used_memory"],
                    "utilization": gpu["used_memory"] / gpu["total_memory"] * 100,
                    "active_tasks": len(gpu["tasks"])
                })
            return status

# Instância global do gerenciador
gpu_manager = GPUManager() 