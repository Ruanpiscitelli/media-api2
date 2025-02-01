"""
Gerenciador unificado de GPUs com suporte a NVLink, balanceamento e failover.
Implementa estratégias de otimização para 4x RTX 4090.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import torch
import pynvml
from prometheus_client import Gauge, start_http_server

from src.config.gpu_config import get_gpu_config
from src.core.cache import Cache
from src.core.errors import InsufficientVRAMError, PreemptionError

# Configuração de logging
logger = logging.getLogger(__name__)

@dataclass
class GPUTask:
    """Representa uma tarefa usando GPU"""
    task_id: str
    gpu_id: int
    vram_required: int
    priority: int = 0
    start_time: Optional[float] = None

@dataclass
class PreemptionCandidate:
    """Representa uma tarefa candidata à preempção"""
    task: GPUTask
    gpu_id: int
    score: float  # Score baseado em prioridade, tempo de execução e uso de VRAM

@dataclass
class PreemptionPlan:
    """Plano de preempção de tarefas"""
    candidates: List[PreemptionCandidate]
    total_vram: int
    affected_gpus: Set[int]

class GPUManager:
    """
    Gerenciador unificado de recursos GPU com:
    - Suporte a NVLink
    - Balanceamento de carga
    - Failover automático
    - Monitoramento em tempo real
    - Cache de predições
    """
    
    def __init__(self):
        """Inicializa o gerenciador unificado de GPUs"""
        self.config = get_gpu_config()
        self.cache = Cache()
        
        # Estado interno
        self.gpus = []
        self.tasks: Dict[str, GPUTask] = {}
        self.failed_gpus: Set[int] = set()
        self.lock = asyncio.Lock()
        
        # Inicialização
        self._init_nvml()
        self._init_gpus()
        self._init_metrics()
        self._start_monitoring()
        
        # Mapa de VRAM por tipo de tarefa
        self.vram_map = {
            'sdxl': 8.5,
            'fish_speech': 4.2,
            'video': 12.0,
            'txt2img': 8.5,
            'img2img': 9.0,
            'inpainting': 9.5,
            'upscale': 4.0,
            'audio': 4.2
        }
        
    def _init_nvml(self):
        """Inicializa NVIDIA Management Library"""
        pynvml.nvmlInit()
        self.num_gpus = pynvml.nvmlDeviceGetCount()
        self.handles = {
            i: pynvml.nvmlDeviceGetHandleByIndex(i)
            for i in range(self.num_gpus)
        }
        
    def _init_gpus(self):
        """Inicializa lista de GPUs disponíveis"""
        if not torch.cuda.is_available():
            logger.warning("CUDA não disponível")
            return
            
        for gpu_id in range(self.num_gpus):
            total_memory = torch.cuda.get_device_properties(gpu_id).total_memory
            self.gpus.append({
                "id": gpu_id,
                "total_memory": total_memory,
                "used_memory": 0,
                "tasks": [],
                "nvlink_peers": self._get_nvlink_peers(gpu_id)
            })
            logger.info(f"GPU {gpu_id} inicializada: {total_memory/1024**3:.1f}GB VRAM")
            
    def _init_metrics(self):
        """Registra métricas Prometheus"""
        self.metrics = {
            'vram_used': Gauge('gpu_vram_used', 'VRAM Utilizada em bytes', ['gpu_id']),
            'vram_total': Gauge('gpu_vram_total', 'VRAM Total em bytes', ['gpu_id']),
            'utilization': Gauge('gpu_utilization', 'Utilização da GPU em %', ['gpu_id']),
            'temperature': Gauge('gpu_temperature', 'Temperatura da GPU em °C', ['gpu_id']),
            'nvlink_speed': Gauge('gpu_nvlink_speed', 'Velocidade NVLink em GB/s', ['gpu_id', 'peer_id']),
            'task_count': Gauge('gpu_task_count', 'Número de tarefas ativas', ['gpu_id']),
            'errors': Gauge('gpu_errors', 'Contagem de erros', ['gpu_id'])
        }
        
        # Inicializa valores
        for gpu in self.gpus:
            gpu_id = gpu['id']
            self.metrics['vram_total'].labels(gpu_id).set(gpu['total_memory'])
            
        # Inicia servidor de métricas
        start_http_server(8001)
            
    def _start_monitoring(self):
        """Inicia loops de monitoramento"""
        async def metrics_loop():
            while True:
                await self._update_metrics()
                await asyncio.sleep(1)
                
        async def health_loop():
            while True:
                await self._check_gpu_health()
                await asyncio.sleep(60)
                
        asyncio.create_task(metrics_loop())
        asyncio.create_task(health_loop())
        
    async def _update_metrics(self):
        """Atualiza métricas de todas as GPUs"""
        for gpu_id, handle in self.handles.items():
            try:
                # Métricas básicas
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                
                self.metrics['vram_used'].labels(gpu_id).set(mem.used)
                self.metrics['utilization'].labels(gpu_id).set(util.gpu)
                self.metrics['temperature'].labels(gpu_id).set(temp)
                self.metrics['task_count'].labels(gpu_id).set(len(self.gpus[gpu_id]['tasks']))
                
                # Métricas NVLink
                for peer_id in self.gpus[gpu_id]['nvlink_peers']:
                    for link in range(pynvml.NVML_NVLINK_MAX_LINKS):
                        try:
                            if pynvml.nvmlDeviceGetNvLinkState(handle, link):
                                speed = pynvml.nvmlDeviceGetNvLinkUtilizationCounter(handle, link, 0)
                                self.metrics['nvlink_speed'].labels(gpu_id, peer_id).set(speed)
                        except pynvml.NVMLError:
                            continue
                            
            except pynvml.NVMLError as e:
                logger.error(f"Erro ao atualizar métricas da GPU {gpu_id}: {e}")
                self.metrics['errors'].labels(gpu_id).inc()
                
    async def _check_gpu_health(self):
        """Verifica saúde das GPUs e gerencia failover"""
        for gpu_id, handle in self.handles.items():
            if gpu_id in self.failed_gpus:
                continue
                
            try:
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                error_count = int(self.metrics['errors'].labels(gpu_id)._value.get())
                
                if temp > self.config['monitoring']['temperature_limit'] or error_count > 10:
                    logger.error(f"GPU {gpu_id} falhou: temp={temp}°C, errors={error_count}")
                    await self._handle_gpu_failure(gpu_id)
                    
            except pynvml.NVMLError as e:
                logger.error(f"Erro ao verificar saúde da GPU {gpu_id}: {e}")
                self.metrics['errors'].labels(gpu_id).inc()
                
    async def _handle_gpu_failure(self, gpu_id: int):
        """Gerencia falha de GPU e redistribui tarefas"""
        async with self.lock:
            self.failed_gpus.add(gpu_id)
            
            # Redistribui tarefas
            tasks_to_move = self.gpus[gpu_id]['tasks'].copy()
            for task_id in tasks_to_move:
                task = self.tasks[task_id]
                new_gpu_id = await self._find_replacement_gpu(task)
                if new_gpu_id is not None:
                    await self._move_task(task, new_gpu_id)
                else:
                    logger.error(f"Não foi possível realocar tarefa {task_id}")
                    
    async def _move_task(self, task: GPUTask, new_gpu_id: int):
        """Move uma tarefa para outra GPU"""
        old_gpu_id = task.gpu_id
        
        # Remove da GPU antiga
        self.gpus[old_gpu_id]['tasks'].remove(task.task_id)
        self.gpus[old_gpu_id]['used_memory'] -= task.vram_required
        
        # Adiciona na nova GPU
        self.gpus[new_gpu_id]['tasks'].append(task.task_id)
        self.gpus[new_gpu_id]['used_memory'] += task.vram_required
        task.gpu_id = new_gpu_id
        
        logger.info(f"Tarefa {task.task_id} movida da GPU {old_gpu_id} para {new_gpu_id}")
        
    def _get_nvlink_peers(self, gpu_id: int) -> List[int]:
        """Retorna lista de GPUs conectadas via NVLink"""
        peers = []
        handle = self.handles[gpu_id]
        
        for link in range(pynvml.NVML_NVLINK_MAX_LINKS):
            try:
                if pynvml.nvmlDeviceGetNvLinkState(handle, link):
                    peer_info = pynvml.nvmlDeviceGetNvLinkRemotePciInfo(handle, link)
                    for i, h in self.handles.items():
                        if i != gpu_id:
                            pci_info = pynvml.nvmlDeviceGetPciInfo(h)
                            if peer_info.busId == pci_info.busId:
                                peers.append(i)
                                break
            except pynvml.NVMLError:
                continue
                
        return list(set(peers))
        
    async def predict_vram_usage(self, task_type: str) -> float:
        """Prediz uso de VRAM com base no tipo de tarefa e histórico"""
        cache_key = f"vram_estimate_{task_type}"
        cached = await self.cache.get(cache_key)
        if cached:
            return float(cached)
            
        base_estimate = self.vram_map.get(task_type, 6.0)
        load_factor = 1 + (len(self.tasks) / len(self.gpus)) if self.gpus else 1
        estimate = base_estimate * load_factor * 1024**3  # Converte para bytes
        
        await self.cache.set(cache_key, estimate, ttl=300)
        return estimate
        
    async def allocate_gpu(self, task_id: str, vram_required: int, priority: int = 0) -> Optional[int]:
        """Aloca GPU para uma tarefa considerando NVLink e balanceamento"""
        async with self.lock:
            # Ordena GPUs por:
            # 1. Número de conexões NVLink
            # 2. Memória livre
            # 3. Número de tarefas
            sorted_gpus = sorted(
                [g for g in self.gpus if g['id'] not in self.failed_gpus],
                key=lambda g: (
                    len(g['nvlink_peers']),
                    g['total_memory'] - g['used_memory'],
                    -len(g['tasks'])
                ),
                reverse=True
            )
            
            for gpu in sorted_gpus:
                free_memory = gpu['total_memory'] - gpu['used_memory']
                if free_memory >= vram_required:
                    gpu['used_memory'] += vram_required
                    task = GPUTask(
                        task_id=task_id,
                        gpu_id=gpu['id'],
                        vram_required=vram_required,
                        priority=priority,
                        start_time=time.time()
                    )
                    self.tasks[task_id] = task
                    gpu['tasks'].append(task_id)
                    logger.info(f"GPU {gpu['id']} alocada para tarefa {task_id}")
                    return gpu['id']
                    
            # Se não encontrou GPU livre, tenta preempção
            return await self._try_preempt_gpu(vram_required, priority)
            
    async def _calculate_preemption_score(self, task: GPUTask, gpu_id: int) -> float:
        """
        Calcula o score de preempção para uma tarefa baseado em:
        - Prioridade da tarefa
        - Tempo de execução
        - Uso de VRAM
        - Impacto no sistema
        
        Retorna score normalizado (0-1), onde maior = melhor candidato para preempção
        """
        runtime = time.time() - task.start_time if task.start_time else 0
        
        # Fatores de peso para cada componente
        PRIORITY_WEIGHT = 0.4
        RUNTIME_WEIGHT = 0.3
        VRAM_WEIGHT = 0.2
        IMPACT_WEIGHT = 0.1
        
        # Normaliza prioridade (menor prioridade = maior score)
        priority_score = 1 - (task.priority / 10)  # Assume prioridade máxima = 10
        
        # Penaliza tarefas rodando há mais tempo
        runtime_score = 1 / (1 + runtime/3600)  # Normaliza para 1 hora
        
        # Favorece tarefas usando mais VRAM
        vram_score = task.vram_required / (24 * 1024**3)  # Normaliza para 24GB
        
        # Avalia impacto do NVLink
        nvlink_impact = len(self.gpus[gpu_id]['nvlink_peers']) / len(self.gpus)
        
        return (
            PRIORITY_WEIGHT * priority_score +
            RUNTIME_WEIGHT * runtime_score +
            VRAM_WEIGHT * vram_score +
            IMPACT_WEIGHT * nvlink_impact
        )

    async def _find_preemption_candidates(self, vram_required: int, priority: int) -> Optional[PreemptionPlan]:
        """
        Encontra o melhor conjunto de tarefas para preempção considerando múltiplas GPUs.
        Implementa uma estratégia gulosa para minimizar o número de preempções.
        """
        all_candidates: List[PreemptionCandidate] = []
        
        # Coleta candidatos de todas as GPUs
        for gpu in self.gpus:
            if gpu['id'] in self.failed_gpus:
                continue
                
            for task_id in gpu['tasks']:
                task = self.tasks[task_id]
                if task.priority >= priority:
                    continue
                    
                score = await self._calculate_preemption_score(task, gpu['id'])
                candidate = PreemptionCandidate(task, gpu['id'], score)
                all_candidates.append(candidate)
                
        if not all_candidates:
            return None
            
        # Ordena candidatos por score (maior primeiro)
        all_candidates.sort(key=lambda c: c.score, reverse=True)
        
        # Encontra melhor combinação de candidatos
        selected_candidates = []
        total_vram = 0
        affected_gpus = set()
        
        for candidate in all_candidates:
            if total_vram >= vram_required:
                break
                
            selected_candidates.append(candidate)
            total_vram += candidate.task.vram_required
            affected_gpus.add(candidate.gpu_id)
            
        if total_vram < vram_required:
            return None
            
        return PreemptionPlan(selected_candidates, total_vram, affected_gpus)

    async def _execute_preemption_plan(self, plan: PreemptionPlan) -> Tuple[bool, Optional[int]]:
        """
        Executa um plano de preempção, com rollback em caso de falha.
        Retorna (sucesso, gpu_id) onde gpu_id é a GPU escolhida para a nova tarefa.
        """
        preempted_tasks = []
        
        try:
            # Executa preempções
            for candidate in plan.candidates:
                await self.release_gpu(candidate.task.task_id)
                preempted_tasks.append(candidate.task)
                logger.info(
                    f"Preemptada tarefa {candidate.task.task_id} da GPU {candidate.gpu_id} "
                    f"(prioridade={candidate.task.priority}, runtime={time.time()-candidate.task.start_time:.1f}s)"
                )
                
            # Escolhe a GPU com mais VRAM livre
            best_gpu = max(
                [g for g in self.gpus if g['id'] in plan.affected_gpus],
                key=lambda g: g['total_memory'] - g['used_memory']
            )
            
            return True, best_gpu['id']
            
        except Exception as e:
            logger.error(f"Erro durante preempção: {str(e)}")
            # Tenta restaurar tarefas preemptadas
            for task in preempted_tasks:
                try:
                    await self.allocate_gpu(task.task_id, task.vram_required, task.priority)
                except Exception as restore_error:
                    logger.error(f"Erro ao restaurar tarefa {task.task_id}: {str(restore_error)}")
            return False, None

    async def _try_preempt_gpu(self, vram_required: int, priority: int) -> Optional[int]:
        """
        Tenta liberar espaço preemptando tarefas de menor prioridade.
        Implementa estratégia multi-GPU com gerenciamento robusto de erros.
        
        Args:
            vram_required: Quantidade de VRAM necessária em bytes
            priority: Prioridade da nova tarefa
            
        Returns:
            ID da GPU alocada ou None se não foi possível preemptar
            
        Raises:
            PreemptionError: Se ocorrer erro durante preempção
        """
        try:
            # Encontra candidatos à preempção
            plan = await self._find_preemption_candidates(vram_required, priority)
            if not plan:
                logger.warning(
                    f"Não foi possível encontrar candidatos para preempção "
                    f"(vram={vram_required/1024**3:.1f}GB, prioridade={priority})"
                )
                return None
                
            # Valida plano
            if len(plan.affected_gpus) > len(self.gpus) // 2:
                logger.warning("Plano de preempção afetaria muitas GPUs, abortando")
                return None
                
            # Executa plano
            success, gpu_id = await self._execute_preemption_plan(plan)
            if not success:
                raise PreemptionError("Falha ao executar plano de preempção")
                
            logger.info(
                f"Preempção bem sucedida: liberados {plan.total_vram/1024**3:.1f}GB "
                f"em {len(plan.affected_gpus)} GPUs"
            )
            return gpu_id
            
        except Exception as e:
            logger.error(f"Erro durante tentativa de preempção: {str(e)}")
            raise PreemptionError(f"Erro durante preempção: {str(e)}")
        
    async def release_gpu(self, task_id: str):
        """Libera GPU alocada para uma tarefa"""
        async with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                gpu = self.gpus[task.gpu_id]
                
                gpu['used_memory'] -= task.vram_required
                gpu['tasks'].remove(task_id)
                del self.tasks[task_id]
                
                logger.info(f"GPU {task.gpu_id} liberada da tarefa {task_id}")
                torch.cuda.empty_cache()
                
    async def get_gpu_status(self) -> List[Dict]:
        """Retorna status detalhado de todas as GPUs"""
        async with self.lock:
            status = []
            for gpu in self.gpus:
                gpu_id = gpu['id']
                handle = self.handles[gpu_id]
                
                try:
                    info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    
                    status.append({
                        'id': gpu_id,
                        'failed': gpu_id in self.failed_gpus,
                        'memory': {
                            'total': info.total,
                            'used': info.used,
                            'free': info.free
                        },
                        'utilization': util.gpu,
                        'temperature': temp,
                        'nvlink_peers': gpu['nvlink_peers'],
                        'active_tasks': len(gpu['tasks']),
                        'tasks': [
                            {
                                'id': tid,
                                'vram': self.tasks[tid].vram_required,
                                'priority': self.tasks[tid].priority,
                                'runtime': time.time() - self.tasks[tid].start_time
                            }
                            for tid in gpu['tasks']
                        ]
                    })
                except pynvml.NVMLError as e:
                    logger.error(f"Erro ao obter status da GPU {gpu_id}: {e}")
                    status.append({
                        'id': gpu_id,
                        'failed': True,
                        'error': str(e)
                    })
                    
            return status
            
    def __del__(self):
        """Cleanup ao destruir o gerenciador"""
        try:
            pynvml.nvmlShutdown()
        except:
            pass

# Instância global
gpu_manager = GPUManager() 