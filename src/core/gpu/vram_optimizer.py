import asyncio
import logging
from typing import Dict, Any, Optional
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class VRAMManager:
    def __init__(self):
        self.models = {
            "SDXL": {"vram": 8000, "loaded": False},
            "FastHuayuan": {"vram": 6000, "loaded": False},
            "ComfyUI": {"vram": 4000, "loaded": False}  # Reserva para ComfyUI
        }
        
        # Cache de estimativas de VRAM por workflow
        self.workflow_vram_estimates: Dict[str, int] = {}
        
        # Carregar estimativas de workflows conhecidos
        self._load_workflow_estimates()
    
    def _load_workflow_estimates(self):
        """Carrega estimativas de VRAM para workflows conhecidos"""
        base_path = Path(__file__).parent.parent.parent
        estimates_path = base_path / "config" / "vram_estimates.json"
        
        if estimates_path.exists():
            try:
                self.workflow_vram_estimates = json.loads(estimates_path.read_text())
                logger.info(f"Carregadas {len(self.workflow_vram_estimates)} estimativas de VRAM")
            except json.JSONDecodeError:
                logger.error("Erro ao carregar estimativas de VRAM")
    
    async def load_model(self, model_name: str):
        """
        Carrega um modelo na VRAM.
        
        Args:
            model_name: Nome do modelo a carregar
        """
        if model_name not in self.models:
            raise ValueError(f"Modelo desconhecido: {model_name}")
        
        # Calcular VRAM total em uso
        vram_in_use = sum(m['vram'] for m in self.models.values() if m['loaded'])
        
        # Se não houver espaço suficiente, descarregar modelos
        if vram_in_use + self.models[model_name]['vram'] > 24000:
            await self.unload_least_used_model()
        
        self.models[model_name]['loaded'] = True
        logger.info(f"Modelo {model_name} carregado na VRAM")
    
    async def unload_least_used_model(self):
        """Descarrega o modelo menos utilizado da VRAM"""
        # Por enquanto, descarrega o primeiro modelo carregado que não seja ComfyUI
        for name, model in self.models.items():
            if model['loaded'] and name != "ComfyUI":
                model['loaded'] = False
                logger.info(f"Modelo {name} descarregado da VRAM")
                return
    
    async def estimate_workflow_vram(self, workflow: Dict[str, Any]) -> int:
        """
        Estima o uso de VRAM de um workflow.
        
        Args:
            workflow: Workflow do ComfyUI
            
        Returns:
            Estimativa de VRAM em MB
        """
        # Calcular hash do workflow para cache
        workflow_str = json.dumps(workflow, sort_keys=True)
        workflow_hash = hash(workflow_str)
        
        # Verificar cache
        if workflow_hash in self.workflow_vram_estimates:
            return self.workflow_vram_estimates[workflow_hash]
        
        # Estimativa básica baseada no número de nós
        base_vram = 4000  # VRAM base para ComfyUI
        vram_per_node = 500  # VRAM estimada por nó
        
        total_vram = base_vram + (len(workflow) * vram_per_node)
        
        # Adicionar ao cache
        self.workflow_vram_estimates[workflow_hash] = total_vram
        
        return total_vram

class VRAMBalancer:
    def __init__(self, gpu_manager):
        self.gpu_manager = gpu_manager
        self.vram_manager = VRAMManager()
    
    async def optimize_allocations(self):
        """Balanceia carga de VRAM entre GPUs"""
        while True:
            gpu_status = await self.gpu_manager.get_status()
            
            # Calcular desbalanceamento
            usage = [g['used_vram'] for g in gpu_status.values()]
            avg = sum(usage) / len(usage)
            
            # Redistribuir tarefas
            for gpu_id, usage in gpu_status.items():
                if usage > avg * 1.2:  # 20% acima da média
                    await self.rebalance_gpu(gpu_id)
            
            await asyncio.sleep(30)
    
    async def rebalance_gpu(self, gpu_id: str):
        """
        Rebalanceia carga de uma GPU específica.
        
        Args:
            gpu_id: ID da GPU a rebalancear
        """
        logger.info(f"Rebalanceando GPU {gpu_id}")
        # Implementar lógica de rebalanceamento

class VRAMOptimizer:
    def __init__(self):
        self.vram_manager = VRAMManager()
        self.workload_tracker = {
            "comfyui": {},  # Tracking de workflows ComfyUI
            "models": {}    # Tracking de outros modelos
        }
    
    async def optimize_allocations(self):
        """Otimiza alocações de VRAM"""
        while True:
            # Otimizar alocações ComfyUI
            if self.workload_tracker["comfyui"]:
                for workflow_id, workflow in self.workload_tracker["comfyui"].items():
                    vram_needed = await self.vram_manager.estimate_workflow_vram(workflow)
                    logger.info(f"Workflow {workflow_id} requer {vram_needed}MB VRAM")
                    
                    # Garantir VRAM suficiente
                    if vram_needed > self.get_available_vram():
                        await self.vram_manager.unload_least_used_model()
            
            # Otimizar alocações de modelos
            for model_name in self.workload_tracker["models"]:
                if not self.vram_manager.models[model_name]["loaded"]:
                    try:
                        await self.vram_manager.load_model(model_name)
                    except ValueError as e:
                        logger.warning(f"Erro ao carregar modelo: {str(e)}")
            
            await asyncio.sleep(30)
    
    def get_available_vram(self) -> int:
        """
        Retorna a quantidade de VRAM disponível.
        
        Returns:
            VRAM disponível em MB
        """
        total_vram = 24000  # Total de VRAM (24GB)
        used_vram = sum(
            model["vram"]
            for model in self.vram_manager.models.values()
            if model["loaded"]
        )
        return total_vram - used_vram