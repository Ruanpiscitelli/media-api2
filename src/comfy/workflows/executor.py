"""
Executor de workflows do ComfyUI.
Gerencia a execução e monitoramento das tarefas.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union

from prometheus_client import Counter, Histogram

from src.comfy.workflows.manager import workflow_manager
from src.core.gpu.manager import gpu_manager

logger = logging.getLogger(__name__)

# Métricas Prometheus
WORKFLOW_COUNTER = Counter(
    "comfy_workflows_total",
    "Total de workflows executados",
    ["template", "status"]
)

WORKFLOW_DURATION = Histogram(
    "comfy_workflow_duration_seconds",
    "Duração dos workflows em segundos",
    ["template"]
)

class WorkflowExecutor:
    """Executor de workflows do ComfyUI."""
    
    def __init__(self):
        """Inicializa o executor de workflows."""
        self.active_workflows: Dict[str, Dict] = {}
        self.poll_interval = 1.0  # Intervalo de polling em segundos
        
    async def execute(
        self,
        template_name: str,
        inputs: Dict[str, Union[str, int, float, Dict]],
        prompt: Optional[str] = None,
        gpu_id: Optional[int] = None
    ) -> str:
        """
        Executa um workflow do ComfyUI.
        
        Args:
            template_name: Nome do template do workflow
            inputs: Dicionário com os inputs do workflow
            prompt: Prompt opcional para geração
            gpu_id: ID da GPU para execução (opcional)
            
        Returns:
            ID da tarefa
        """
        # Aloca GPU se necessário
        if gpu_id is None:
            gpu_id = await gpu_manager.allocate_gpu()
            
        try:
            # Carrega e executa o workflow
            workflow = await workflow_manager.load_workflow(template_name)
            prompt_id = await workflow_manager.execute_workflow(
                workflow=workflow,
                inputs=inputs,
                prompt=prompt
            )
            
            # Registra workflow ativo
            self.active_workflows[prompt_id] = {
                "template": template_name,
                "gpu_id": gpu_id,
                "status": "running"
            }
            
            # Inicia monitoramento
            asyncio.create_task(self._monitor_workflow(prompt_id))
            
            # Métricas
            WORKFLOW_COUNTER.labels(
                template=template_name,
                status="started"
            ).inc()
            
            return prompt_id
            
        except Exception as e:
            logger.error(f"Erro ao executar workflow {template_name}: {e}")
            if gpu_id is not None:
                await gpu_manager.release_gpu(gpu_id)
            raise
            
    async def get_status(self, prompt_id: str) -> Dict:
        """Retorna o status de um workflow."""
        if prompt_id not in self.active_workflows:
            raise ValueError(f"Workflow {prompt_id} não encontrado")
            
        try:
            status = await workflow_manager.get_workflow_status(prompt_id)
            return {
                **self.active_workflows[prompt_id],
                **status
            }
        except Exception as e:
            logger.error(f"Erro ao obter status do workflow {prompt_id}: {e}")
            raise
            
    async def list_active(self) -> List[Dict]:
        """Lista todos os workflows ativos."""
        return [
            {
                "prompt_id": k,
                **v
            }
            for k, v in self.active_workflows.items()
        ]
        
    async def _monitor_workflow(self, prompt_id: str) -> None:
        """Monitora um workflow em execução."""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            try:
                status = await workflow_manager.get_workflow_status(prompt_id)
                
                if status.get("completed"):
                    # Workflow concluído com sucesso
                    duration = asyncio.get_event_loop().time() - start_time
                    template = self.active_workflows[prompt_id]["template"]
                    
                    # Libera GPU
                    gpu_id = self.active_workflows[prompt_id]["gpu_id"]
                    if gpu_id is not None:
                        await gpu_manager.release_gpu(gpu_id)
                    
                    # Atualiza status
                    self.active_workflows[prompt_id]["status"] = "completed"
                    
                    # Métricas
                    WORKFLOW_COUNTER.labels(
                        template=template,
                        status="completed"
                    ).inc()
                    WORKFLOW_DURATION.labels(template=template).observe(duration)
                    
                    break
                    
                elif status.get("error"):
                    # Workflow falhou
                    logger.error(f"Workflow {prompt_id} falhou: {status['error']}")
                    
                    # Libera GPU
                    gpu_id = self.active_workflows[prompt_id]["gpu_id"]
                    if gpu_id is not None:
                        await gpu_manager.release_gpu(gpu_id)
                    
                    # Atualiza status
                    self.active_workflows[prompt_id]["status"] = "failed"
                    self.active_workflows[prompt_id]["error"] = status["error"]
                    
                    # Métricas
                    WORKFLOW_COUNTER.labels(
                        template=self.active_workflows[prompt_id]["template"],
                        status="failed"
                    ).inc()
                    
                    break
                    
            except Exception as e:
                logger.error(f"Erro ao monitorar workflow {prompt_id}: {e}")
                break
                
            await asyncio.sleep(self.poll_interval)
            
        # Remove workflow da lista de ativos
        self.active_workflows.pop(prompt_id, None)

# Instância global do executor
workflow_executor = WorkflowExecutor() 