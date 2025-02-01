"""
Gerenciador de GPUs para alocação e monitoramento de recursos.
Implementa estratégias de otimização para 4x RTX 4090.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
import torch
import nvidia_smi
from prometheus_client import Gauge

from src.config.gpu_config import (
    get_gpu_config,
    get_pipeline_config,
    get_cache_config
)

# Configuração de logging
logger = logging.getLogger(__name__)

# Métricas Prometheus
GPU_MEMORY_USED = Gauge('gpu_memory_used_bytes', 'GPU memory used in bytes', ['device'])
GPU_UTILIZATION = Gauge('gpu_utilization_percent', 'GPU utilization percentage', ['device'])
GPU_TEMPERATURE = Gauge('gpu_temperature_celsius', 'GPU temperature in Celsius', ['device'])

class GPUManager:
    """
    Gerenciador de recursos GPU com suporte a múltiplas GPUs e otimização de carga.
    """
    
    def __init__(self):
        """
        Inicializa o gerenciador de GPUs com as configurações do sistema.
        """
        self.config = get_gpu_config()
        self.pipeline_config = get_pipeline_config()
        self.cache_config = get_cache_config()
        
        # Inicializa NVIDIA Management Library
        nvidia_smi.nvmlInit()
        
        # Estado interno
        self._gpu_locks = {
            device: asyncio.Lock() 
            for device in self.config['devices']
        }
        self._active_tasks = {}
        self._device_handles = {}
        
        # Configura CUDA
        self._setup_cuda()
        
        # Inicia monitoramento
        self._start_monitoring()
    
    def _setup_cuda(self):
        """
        Configura ambiente CUDA com otimizações.
        """
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA não está disponível no sistema")
            
        # Configura otimizações
        torch.backends.cuda.matmul.allow_tf32 = self.config['optimization']['enable_tf32']
        torch.backends.cudnn.benchmark = self.config['optimization']['enable_cudnn_benchmarks']
        
        # Inicializa handles das GPUs
        for device in self.config['devices']:
            handle = nvidia_smi.nvmlDeviceGetHandleByIndex(device)
            self._device_handles[device] = handle
    
    def _start_monitoring(self):
        """
        Inicia o loop de monitoramento das GPUs.
        """
        async def monitoring_loop():
            while True:
                await self._update_metrics()
                await asyncio.sleep(self.config['monitoring']['metrics_interval'])
        
        asyncio.create_task(monitoring_loop())
    
    async def _update_metrics(self):
        """
        Atualiza métricas de todas as GPUs.
        """
        for device in self.config['devices']:
            handle = self._device_handles[device]
            
            # Coleta métricas
            info = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
            temp = nvidia_smi.nvmlDeviceGetTemperature(handle, nvidia_smi.NVML_TEMPERATURE_GPU)
            util = nvidia_smi.nvmlDeviceGetUtilizationRates(handle)
            
            # Atualiza métricas Prometheus
            GPU_MEMORY_USED.labels(device=device).set(info.used)
            GPU_TEMPERATURE.labels(device=device).set(temp)
            GPU_UTILIZATION.labels(device=device).set(util.gpu)
            
            # Verifica limites
            if temp > self.config['monitoring']['temperature_limit']:
                logger.warning(f"GPU {device} acima do limite de temperatura: {temp}°C")
            
            if util.gpu > self.config['monitoring']['utilization_threshold']:
                logger.warning(f"GPU {device} acima do limite de utilização: {util.gpu}%")
    
    async def allocate_gpu(self, task_type: str, memory_required: int) -> Optional[int]:
        """
        Aloca uma GPU para uma tarefa específica.
        
        Args:
            task_type: Tipo da tarefa ('image', 'speech', 'video')
            memory_required: Memória necessária em MB
            
        Returns:
            ID da GPU alocada ou None se não houver GPU disponível
        """
        # Verifica GPUs prioritárias para o tipo de tarefa
        priority_devices = self.config['priorities'].get(task_type, self.config['devices'])
        
        for device in priority_devices:
            if await self._can_allocate(device, memory_required):
                async with self._gpu_locks[device]:
                    # Registra alocação
                    self._active_tasks[id(asyncio.current_task())] = device
                    logger.info(f"GPU {device} alocada para tarefa {task_type}")
                    return device
        
        # Tenta GPUs não prioritárias
        for device in self.config['devices']:
            if device not in priority_devices:
                if await self._can_allocate(device, memory_required):
                    async with self._gpu_locks[device]:
                        self._active_tasks[id(asyncio.current_task())] = device
                        logger.info(f"GPU {device} (não prioritária) alocada para tarefa {task_type}")
                        return device
        
        logger.warning(f"Não foi possível alocar GPU para tarefa {task_type}")
        return None
    
    async def _can_allocate(self, device: int, memory_required: int) -> bool:
        """
        Verifica se uma GPU pode ser alocada para uma tarefa.
        
        Args:
            device: ID da GPU
            memory_required: Memória necessária em MB
            
        Returns:
            True se a GPU pode ser alocada, False caso contrário
        """
        handle = self._device_handles[device]
        info = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
        
        # Converte para MB
        free_memory = info.free / (1024 * 1024)
        
        # Considera headroom de memória
        available = free_memory - self.config['fallback']['memory_headroom']
        
        return available >= memory_required
    
    async def release_gpu(self, device: Optional[int] = None):
        """
        Libera uma GPU alocada.
        
        Args:
            device: ID da GPU a ser liberada. Se None, libera a GPU da tarefa atual.
        """
        if device is None:
            task_id = id(asyncio.current_task())
            device = self._active_tasks.pop(task_id, None)
            
        if device is not None:
            logger.info(f"GPU {device} liberada")
            
            # Força limpeza de cache CUDA
            torch.cuda.empty_cache()
    
    async def get_gpu_status(self) -> List[Dict]:
        """
        Retorna status detalhado de todas as GPUs.
        
        Returns:
            Lista com informações de cada GPU
        """
        status = []
        
        for device in self.config['devices']:
            handle = self._device_handles[device]
            
            # Coleta informações
            info = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
            temp = nvidia_smi.nvmlDeviceGetTemperature(handle, nvidia_smi.NVML_TEMPERATURE_GPU)
            util = nvidia_smi.nvmlDeviceGetUtilizationRates(handle)
            
            status.append({
                'device': device,
                'memory': {
                    'total': info.total / (1024 * 1024),  # MB
                    'used': info.used / (1024 * 1024),
                    'free': info.free / (1024 * 1024)
                },
                'temperature': temp,
                'utilization': {
                    'gpu': util.gpu,
                    'memory': util.memory
                },
                'active_tasks': len([
                    task for task, dev in self._active_tasks.items()
                    if dev == device
                ])
            })
        
        return status
    
    def __del__(self):
        """
        Cleanup ao destruir o gerenciador.
        """
        try:
            nvidia_smi.nvmlShutdown()
        except:
            pass 

class GPUMonitor:
    def __init__(self):
        """
        Inicializa o monitor com 4 GPUs RTX 4090.
        Cada GPU tem 24GB de VRAM (24576 MB).
        """
        self.gpus = [
            {
                "id": 0,
                "name": "RTX 4090-1",
                "total_vram": 24576,  # 24GB em MB
                "allocated_vram": 0,
                "temperature": 0,
                "utilization": 0,
                "processes": []
            },
            {
                "id": 1,
                "name": "RTX 4090-2",
                "total_vram": 24576,  # 24GB em MB
                "allocated_vram": 0,
                "temperature": 0,
                "utilization": 0,
                "processes": []
            },
            {
                "id": 2,
                "name": "RTX 4090-3",
                "total_vram": 24576,  # 24GB em MB
                "allocated_vram": 0,
                "temperature": 0,
                "utilization": 0,
                "processes": []
            },
            {
                "id": 3,
                "name": "RTX 4090-4",
                "total_vram": 24576,  # 24GB em MB
                "allocated_vram": 0,
                "temperature": 0,
                "utilization": 0,
                "processes": []
            }
        ]
    
    async def allocate_task(self, task):
        """
        Aloca uma tarefa na GPU com menor utilização de VRAM disponível.
        
        Args:
            task: Tarefa a ser alocada com atributo estimated_vram
            
        Returns:
            ID da GPU alocada
            
        Raises:
            NoGPUAvailableError: Se não houver GPU com VRAM suficiente
        """
        suitable_gpus = sorted(
            [g for g in self.gpus if g['total_vram'] - g['allocated_vram'] >= task.estimated_vram],
            key=lambda x: x['allocated_vram']  # Ordena por VRAM alocada em ordem crescente
        )
        
        if not suitable_gpus:
            raise NoGPUAvailableError("No GPUs with sufficient VRAM")
            
        selected_gpu = suitable_gpus[0]
        selected_gpu['allocated_vram'] += task.estimated_vram
        selected_gpu['processes'].append(task.id)
        return selected_gpu['id'] 