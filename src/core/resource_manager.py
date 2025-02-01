"""
Gerenciador de recursos do sistema.
Controla alocação de GPU, memória e outros recursos.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
import psutil
import torch
import numpy as np
from dataclasses import dataclass
from prometheus_client import Gauge, Counter, Histogram
from src.core.gpu.manager import gpu_manager
from src.core.cache.manager import cache_manager

logger = logging.getLogger(__name__)

# Métricas Prometheus
RESOURCE_USAGE = Gauge(
    "resource_usage",
    "Uso de recursos do sistema",
    ["resource_type", "resource_id"]
)

ALLOCATION_TIME = Histogram(
    "resource_allocation_seconds",
    "Tempo de alocação de recursos",
    ["resource_type"]
)

ALLOCATION_ERRORS = Counter(
    "resource_allocation_errors_total",
    "Total de erros de alocação",
    ["resource_type", "error_type"]
)

@dataclass
class ResourceAllocation:
    """Representa uma alocação de recursos."""
    gpu_ids: List[int]
    vram_reserved: Dict[int, float]  # GB por GPU
    ram_reserved: float  # GB
    created_at: float
    priority: int
    task_id: str

class ResourceManager:
    def __init__(self):
        self.cache = cache_manager.get_cache("resources")
        
        # Configurações
        self.max_vram_per_task = 8.0  # GB
        self.max_ram_per_task = 16.0  # GB
        self.vram_buffer = 1.0  # GB de buffer
        self.ram_buffer = 2.0   # GB de buffer
        
        # Estado interno
        self._allocations: Dict[str, ResourceAllocation] = {}
        self._lock = asyncio.Lock()
    
    async def allocate_resources(
        self,
        task_id: str,
        vram_required: float,
        ram_required: float,
        priority: int = 0,
        gpu_preference: Optional[int] = None
    ) -> ResourceAllocation:
        """
        Aloca recursos para uma tarefa.
        
        Args:
            task_id: ID da tarefa
            vram_required: VRAM necessária em GB
            ram_required: RAM necessária em GB
            priority: Prioridade da tarefa (maior = mais prioritário)
            gpu_preference: ID da GPU preferida (opcional)
            
        Returns:
            Alocação de recursos
            
        Raises:
            RuntimeError: Se recursos insuficientes
        """
        async with self._lock:
            try:
                with ALLOCATION_TIME.labels("gpu").time():
                    # Verificar RAM do sistema
                    if not await self._check_system_ram(ram_required):
                        await self._free_resources("ram", ram_required)
                    
                    # Selecionar GPUs apropriadas
                    gpu_ids = await self._select_gpus(
                        vram_required,
                        gpu_preference
                    )
                    
                    # Criar alocação
                    allocation = ResourceAllocation(
                        gpu_ids=gpu_ids,
                        vram_reserved={
                            gpu_id: vram_required for gpu_id in gpu_ids
                        },
                        ram_reserved=ram_required,
                        created_at=asyncio.get_event_loop().time(),
                        priority=priority,
                        task_id=task_id
                    )
                    
                    # Registrar alocação
                    self._allocations[task_id] = allocation
                    
                    # Atualizar métricas
                    self._update_metrics()
                    
                    return allocation
                    
            except Exception as e:
                ALLOCATION_ERRORS.labels(
                    resource_type="gpu",
                    error_type=type(e).__name__
                ).inc()
                raise
    
    async def release_resources(self, task_id: str):
        """Libera recursos alocados para uma tarefa."""
        async with self._lock:
            if task_id in self._allocations:
                allocation = self._allocations.pop(task_id)
                
                # Atualizar métricas
                self._update_metrics()
                
                logger.info(f"Recursos liberados para tarefa {task_id}")
    
    async def get_resource_status(self) -> Dict[str, Any]:
        """Retorna status atual dos recursos."""
        gpus = await gpu_manager.get_available_gpus()
        
        status = {
            "gpus": [
                {
                    "id": gpu.id,
                    "total_vram": gpu.total_vram,
                    "used_vram": gpu.used_vram,
                    "temperature": await gpu.get_temperature(),
                    "utilization": await gpu.get_utilization()
                }
                for gpu in gpus
            ],
            "system": {
                "total_ram": psutil.virtual_memory().total / (1024**3),
                "used_ram": psutil.virtual_memory().used / (1024**3),
                "cpu_percent": psutil.cpu_percent()
            },
            "allocations": len(self._allocations)
        }
        
        return status
    
    async def _check_system_ram(self, required_ram: float) -> bool:
        """Verifica se há RAM suficiente disponível."""
        vm = psutil.virtual_memory()
        available_gb = vm.available / (1024**3)
        
        return available_gb >= (required_ram + self.ram_buffer)
    
    async def _select_gpus(
        self,
        vram_required: float,
        preferred_gpu: Optional[int] = None
    ) -> List[int]:
        """Seleciona GPUs apropriadas para a tarefa."""
        gpus = await gpu_manager.get_available_gpus()
        
        if preferred_gpu is not None:
            # Tentar usar GPU preferida
            gpu = next((g for g in gpus if g.id == preferred_gpu), None)
            if gpu and (gpu.total_vram - gpu.used_vram) >= (vram_required + self.vram_buffer):
                return [gpu.id]
        
        # Ordenar GPUs por VRAM disponível
        gpus = sorted(
            gpus,
            key=lambda g: (g.total_vram - g.used_vram),
            reverse=True
        )
        
        selected_gpus = []
        remaining_vram = vram_required
        
        for gpu in gpus:
            free_vram = gpu.total_vram - gpu.used_vram
            if free_vram >= (remaining_vram + self.vram_buffer):
                selected_gpus.append(gpu.id)
                break
        
        if not selected_gpus:
            raise RuntimeError(
                f"VRAM insuficiente. Necessário: {vram_required}GB"
            )
        
        return selected_gpus
    
    async def _free_resources(
        self,
        resource_type: str,
        required_amount: float
    ):
        """
        Libera recursos terminando tarefas menos prioritárias.
        
        Args:
            resource_type: Tipo de recurso ("ram" ou "vram")
            required_amount: Quantidade necessária em GB
        """
        if not self._allocations:
            return
            
        # Ordenar alocações por prioridade (menor primeiro)
        sorted_allocations = sorted(
            self._allocations.items(),
            key=lambda x: (x[1].priority, -x[1].created_at)
        )
        
        freed_amount = 0
        
        for task_id, allocation in sorted_allocations:
            if resource_type == "ram":
                freed_amount += allocation.ram_reserved
            else:
                freed_amount += sum(allocation.vram_reserved.values())
            
            # Liberar recursos
            await self.release_resources(task_id)
            
            if freed_amount >= required_amount:
                break
    
    def _update_metrics(self):
        """Atualiza métricas Prometheus."""
        # Uso de VRAM por GPU
        for gpu_id, allocation in self._get_gpu_allocations().items():
            RESOURCE_USAGE.labels(
                resource_type="vram",
                resource_id=gpu_id
            ).set(allocation)
        
        # Uso total de RAM
        total_ram = sum(
            alloc.ram_reserved for alloc in self._allocations.values()
        )
        RESOURCE_USAGE.labels(
            resource_type="ram",
            resource_id="total"
        ).set(total_ram)
    
    def _get_gpu_allocations(self) -> Dict[int, float]:
        """Retorna uso atual de VRAM por GPU."""
        gpu_usage = {}
        
        for allocation in self._allocations.values():
            for gpu_id, vram in allocation.vram_reserved.items():
                gpu_usage[gpu_id] = gpu_usage.get(gpu_id, 0) + vram
        
        return gpu_usage

# Instância global do gerenciador
resource_manager = ResourceManager() 