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
import pynvml
from prometheus_client import Gauge
from src.core.cache import Cache

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
    """Gerenciador de recursos de GPU com monitoramento Prometheus"""
    
    def __init__(self):
        """Inicializa o gerenciador GPU"""
        self.gpus = []
        self.tasks: Dict[str, GPUTask] = {}
        self.lock = asyncio.Lock()
        self._initialize_gpus()
        self._init_metrics()
        self.vram_map = {
            'sdxl': 8.5,
            'fish_speech': 4.2,
            'video': 12.0
        }
        self.cache = Cache()
        
        # Add default VRAM requirements for different workflow types
        self.workflow_vram_requirements = {
            'txt2img': 8.5 * 1024**3,  # 8.5GB
            'img2img': 9.0 * 1024**3,  # 9GB
            'inpainting': 9.5 * 1024**3,  # 9.5GB
            'upscale': 4.0 * 1024**3,  # 4GB
            'video': 12.0 * 1024**3,  # 12GB
            'audio': 4.2 * 1024**3,  # 4.2GB
        }
        
    def _initialize_gpus(self):
        """Inicializa lista de GPUs disponíveis"""
        if not torch.cuda.is_available():
            logger.warning("CUDA não disponível. Usando CPU.")
            return
            
        for gpu_id in range(torch.cuda.device_count()):
            total_memory = torch.cuda.get_device_properties(gpu_id).total_memory
            self.gpus.append({
                "id": gpu_id,
                "total_memory": total_memory,
                "used_memory": 0,
                "tasks": []
            })
            logger.info(f"GPU {gpu_id} inicializada: {total_memory/1024**3:.1f}GB VRAM")
    
    def _init_metrics(self):
        """Registra métricas Prometheus para monitoramento de GPUs"""
        self.utilization = Gauge('gpu_utilization', 'Utilização da GPU', ['gpu_id'])
        self.memory_used = Gauge('gpu_memory_used', 'VRAM utilizada', ['gpu_id'])
        self.temperature = Gauge('gpu_temperature', 'Temperatura da GPU', ['gpu_id'])

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
            if not self.gpus:
                return None
                
            # Encontrar GPU com memória suficiente
            for gpu in self.gpus:
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
        for gpu in self.gpus:
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
            for gpu in self.gpus:
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
            for gpu in self.gpus:
                status.append({
                    "id": gpu["id"],
                    "total_memory": gpu["total_memory"],
                    "used_memory": gpu["used_memory"],
                    "free_memory": gpu["total_memory"] - gpu["used_memory"],
                    "utilization": gpu["used_memory"] / gpu["total_memory"] * 100,
                    "active_tasks": len(gpu["tasks"])
                })
            return status

    async def _predict_vram_usage(self, model_type: str) -> float:
        """Preve o uso de VRAM com base no modelo e histórico"""
        # Consulta cache de estimativas
        cache_key = f"vram_estimate_{model_type}"
        cached = await self.cache.get(cache_key)
        if cached:
            return float(cached)
        
        # Calcula estimativa dinâmica
        base_estimate = self.vram_map.get(model_type, 6.0)
        
        # Ajuste baseado na carga atual
        load_factor = 1 + (len(self.tasks) / len(self.gpus)) if self.gpus else 1
        estimate = base_estimate * load_factor * 1024**3  # Convert to bytes
        
        # Atualiza cache
        await self.cache.set(cache_key, estimate, ttl=300)
        return estimate

    async def check_nvlink_peers(self, gpu_id: int) -> List[int]:
        """
        Retorna lista de GPUs conectadas via NVLink.
        
        Args:
            gpu_id: ID da GPU para verificar conexões NVLink
            
        Returns:
            Lista de IDs das GPUs conectadas via NVLink
        """
        peers = []
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
            
            # Verifica cada link NVLink possível
            for link in range(6):
                try:
                    # Verifica se o link está ativo
                    if pynvml.nvmlDeviceGetNvLinkState(handle, link) == pynvml.NVML_FEATURE_ENABLED:
                        # Obtém informações do peer conectado
                        peer_info = pynvml.nvmlDeviceGetNvLinkRemotePciInfo(handle, link)
                        
                        # Encontra o ID da GPU correspondente ao PCI info
                        for i in range(pynvml.nvmlDeviceGetCount()):
                            peer_handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                            if pynvml.nvmlDeviceGetPciInfo(peer_handle).busId == peer_info.busId:
                                if i not in peers and i != gpu_id:
                                    peers.append(i)
                                break
                except pynvml.NVMLError as e:
                    logger.debug(f"Link {link} não disponível para GPU {gpu_id}: {e}")
                    continue
                
        except pynvml.NVMLError as e:
            logger.error(f"Erro ao verificar peers NVLink para GPU {gpu_id}: {e}")
            return []
        
        return peers

    async def estimate_resources(self, workflow: dict) -> dict:
        """
        Estima recursos necessários para executar um workflow.
        
        Args:
            workflow: Dicionário do workflow ComfyUI
            
        Returns:
            Dict com recursos estimados:
                - vram_required: VRAM necessária em bytes
                - estimated_time: Tempo estimado em segundos
        """
        try:
            # Identificar tipo de workflow baseado nos nós
            workflow_type = self._identify_workflow_type(workflow)
            
            # Obter requisito base de VRAM
            base_vram = self.workflow_vram_requirements.get(
                workflow_type, 
                6.0 * 1024**3  # 6GB default
            )
            
            # Ajustar baseado na complexidade
            node_count = len(workflow.get('nodes', []))
            complexity_factor = 1.0 + (node_count / 20)  # +5% por cada 20 nós
            
            vram_required = int(base_vram * complexity_factor)
            
            # Estimar tempo baseado na complexidade
            base_time = 10  # 10 segundos base
            estimated_time = int(base_time * complexity_factor)
            
            return {
                "vram_required": vram_required,
                "estimated_time": estimated_time,
                "workflow_type": workflow_type
            }
            
        except Exception as e:
            logger.error(f"Erro estimando recursos: {e}")
            # Fallback para estimativas conservadoras
            return {
                "vram_required": 8 * 1024**3,  # 8GB
                "estimated_time": 30,
                "workflow_type": "unknown"
            }

    def _identify_workflow_type(self, workflow: dict) -> str:
        """Identifica o tipo do workflow baseado nos nós presentes"""
        nodes = workflow.get('nodes', [])
        node_types = {node.get('class_type', '').lower() for node in nodes}
        
        if any('video' in nt for nt in node_types):
            return 'video'
        elif any('audio' in nt for nt in node_types):
            return 'audio'
        elif any('upscale' in nt for nt in node_types):
            return 'upscale'
        elif any('inpaint' in nt for nt in node_types):
            return 'inpainting'
        elif any('img2img' in nt for nt in node_types):
            return 'img2img'
        elif any('txt2img' in nt for nt in node_types):
            return 'txt2img'
        return 'unknown'

    async def allocate_gpu_for_task(self, task: 'GenerationTask') -> int:
        """
        Novo método para alocação baseada em task object.
        Mantém compatibilidade com interface antiga através de delegation.
        """
        required_vram = await self._predict_vram_usage(task.model_type)
        
        # Prioriza GPUs com NVLink
        for gpu in sorted(self.gpus, 
                         key=lambda x: len(self.check_nvlink_peers(x['id'])), 
                         reverse=True):
            if gpu['total_memory'] - gpu['used_memory'] >= required_vram:
                return gpu['id']
                
        return await self.allocate_gpu(
            task_id=task.id,
            vram_required=required_vram,
            priority=task.priority
        )

# Instância global do gerenciador
gpu_manager = GPUManager() 