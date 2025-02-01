"""
Serviço para otimização de workflows do ComfyUI.
Implementa estratégias para melhorar performance e uso de recursos.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import torch
from src.core.gpu.manager import gpu_manager
from src.core.cache.manager import cache_manager

logger = logging.getLogger(__name__)

class WorkflowOptimizer:
    def __init__(self):
        self.cache = cache_manager.get_cache("workflow")
        
        # Configurações de otimização
        self.vram_threshold = 0.8  # 80% de uso máximo de VRAM
        self.batch_size_limit = 4  # Limite de batch size
        self.max_concurrent = 2    # Máximo de workflows concorrentes por GPU
        
        # Carregar estimativas de VRAM
        self.vram_estimates = self._load_vram_estimates()
    
    def _load_vram_estimates(self) -> Dict[str, float]:
        """Carrega estimativas de uso de VRAM por nó."""
        try:
            estimates_path = Path(__file__).parent.parent / "config" / "vram_estimates.json"
            with open(estimates_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar estimativas de VRAM: {e}")
            return {}
    
    async def optimize_workflow(
        self,
        workflow: Dict[str, Any],
        gpu_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Otimiza um workflow para melhor performance.
        
        Args:
            workflow: Workflow a otimizar
            gpu_id: ID da GPU específica (opcional)
            
        Returns:
            Workflow otimizado
        """
        # Clonar workflow para não modificar original
        optimized = workflow.copy()
        
        # Estimar uso de VRAM
        vram_usage = self._estimate_vram_usage(optimized)
        
        # Selecionar GPU apropriada
        if gpu_id is None:
            gpu_id = await self._select_best_gpu(vram_usage)
        
        # Aplicar otimizações
        optimized = await self._apply_optimizations(
            optimized,
            gpu_id,
            vram_usage
        )
        
        return optimized
    
    def _estimate_vram_usage(self, workflow: Dict[str, Any]) -> float:
        """Estima uso total de VRAM do workflow."""
        total_vram = 0
        
        for node in workflow.get("nodes", []):
            node_type = node.get("type", "")
            
            # Usar estimativa do nó ou valor padrão
            node_vram = self.vram_estimates.get(node_type, 0.5)  # 0.5GB padrão
            
            # Ajustar baseado em parâmetros
            if "batch_size" in node.get("inputs", {}):
                node_vram *= node["inputs"]["batch_size"]
            
            total_vram += node_vram
        
        return total_vram
    
    async def _select_best_gpu(self, required_vram: float) -> int:
        """Seleciona a melhor GPU disponível."""
        gpus = await gpu_manager.get_available_gpus()
        
        best_gpu = None
        best_score = float("-inf")
        
        for gpu in gpus:
            # Calcular score baseado em VRAM livre e carga
            free_vram = gpu.total_vram - gpu.used_vram
            current_load = await gpu.get_utilization()
            
            if free_vram >= required_vram:
                # Score considera VRAM livre e inverso da carga
                score = free_vram * (100 - current_load) / 100
                
                if score > best_score:
                    best_score = score
                    best_gpu = gpu
        
        if best_gpu is None:
            raise RuntimeError("Nenhuma GPU com VRAM suficiente disponível")
            
        return best_gpu.id
    
    async def _apply_optimizations(
        self,
        workflow: Dict[str, Any],
        gpu_id: int,
        vram_usage: float
    ) -> Dict[str, Any]:
        """Aplica otimizações ao workflow."""
        gpu = await gpu_manager.get_gpu(gpu_id)
        
        # Ajustar batch size se necessário
        if vram_usage > gpu.total_vram * self.vram_threshold:
            workflow = self._adjust_batch_sizes(workflow)
        
        # Otimizar ordem dos nós
        workflow = self._optimize_node_order(workflow)
        
        # Adicionar nós de otimização
        workflow = self._add_optimization_nodes(workflow)
        
        return workflow
    
    def _adjust_batch_sizes(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Ajusta batch sizes para otimizar uso de VRAM."""
        for node in workflow.get("nodes", []):
            if "inputs" in node and "batch_size" in node["inputs"]:
                current_batch = node["inputs"]["batch_size"]
                
                # Reduzir batch size se maior que limite
                if current_batch > self.batch_size_limit:
                    node["inputs"]["batch_size"] = self.batch_size_limit
        
        return workflow
    
    def _optimize_node_order(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Otimiza ordem de execução dos nós."""
        nodes = workflow.get("nodes", [])
        
        # Ordenar nós por dependências
        ordered_nodes = []
        visited = set()
        
        def visit_node(node_id):
            if node_id in visited:
                return
            visited.add(node_id)
            
            # Visitar nós dependentes primeiro
            node = nodes[node_id]
            for input_id in node.get("inputs", {}).values():
                if isinstance(input_id, int):
                    visit_node(input_id)
            
            ordered_nodes.append(node)
        
        for i in range(len(nodes)):
            visit_node(i)
        
        workflow["nodes"] = ordered_nodes
        return workflow
    
    def _add_optimization_nodes(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Adiciona nós de otimização ao workflow."""
        nodes = workflow.get("nodes", [])
        
        # Adicionar nós de cleanup após operações pesadas
        for i, node in enumerate(nodes):
            if node["type"] in ["KSampler", "VAEDecode"]:
                cleanup_node = {
                    "type": "CleanupNode",
                    "inputs": {"previous": i}
                }
                nodes.append(cleanup_node)
        
        workflow["nodes"] = nodes
        return workflow

# Instância global do otimizador
workflow_optimizer = WorkflowOptimizer() 