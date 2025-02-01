"""
Pipeline completo de geração de imagens.
Integra SDXL, ComfyUI e sistema de LoRAs.
"""

import logging
from typing import Dict, List, Optional
import torch
from prometheus_client import Summary, Histogram, Gauge

from src.core.config import settings
from src.core.exceptions import PipelineError
from .sdxl.generator import SDXLGenerator
from .lora.manager import LoraManager
from src.comfy.workflows.manager import workflow_manager

logger = logging.getLogger(__name__)

# Métricas Prometheus
PIPELINE_TIME = Summary(
    'image_pipeline_seconds',
    'Time spent in image generation pipeline'
)

PROMPT_LENGTH = Histogram(
    'prompt_length_chars',
    'Distribution of prompt lengths',
    buckets=(10, 50, 100, 200, 500, 1000)
)

GPU_MEMORY = Gauge(
    'pipeline_gpu_memory_bytes',
    'GPU memory usage in pipeline',
    ['device_id']
)

class ImageRequest:
    """Modelo para requisição de geração de imagem."""
    def __init__(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        batch_size: int = 1,
        seed: Optional[int] = None,
        loras: Optional[List[Dict[str, float]]] = None,
        workflow: Optional[str] = None,
        style: Optional[str] = None
    ):
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.width = width
        self.height = height
        self.num_inference_steps = num_inference_steps
        self.guidance_scale = guidance_scale
        self.batch_size = batch_size
        self.seed = seed
        self.loras = loras or []
        self.workflow = workflow or "base"
        self.style = style or "default"
        
class ImagePipeline:
    """
    Pipeline completo para geração de imagens.
    Integra SDXL, ComfyUI e sistema de LoRAs.
    """
    
    def __init__(self):
        """Inicializa o pipeline com todos os componentes."""
        self.sdxl = SDXLGenerator()
        self.lora_manager = LoraManager()
        
        # Carrega workflows e LoRAs
        self._initialize()
        
    async def _initialize(self):
        """Inicialização assíncrona dos componentes."""
        try:
            # Carrega workflows
            await workflow_manager.load_templates()
            
            # Escaneia LoRAs disponíveis
            await self.lora_manager.scan_loras()
            
        except Exception as e:
            logger.error(f"Erro na inicialização do pipeline: {e}")
            raise PipelineError(f"Falha na inicialização: {e}")
            
    @PIPELINE_TIME.time()
    async def generate(self, request: ImageRequest) -> Dict:
        """
        Pipeline completo de geração de imagens.
        
        Args:
            request: Requisição de geração
            
        Returns:
            Dicionário com resultados e metadados
        """
        try:
            # Registra métricas
            PROMPT_LENGTH.observe(len(request.prompt))
            self._update_memory_stats()
            
            # Prepara workflow se especificado
            if request.workflow != "base":
                workflow = await workflow_manager.load_workflow(request.workflow)
                workflow = await workflow_manager.prepare_workflow(
                    workflow,
                    request.prompt,
                    {
                        'negative_prompt': request.negative_prompt,
                        'steps': request.num_inference_steps,
                        'cfg': request.guidance_scale,
                        'seed': request.seed
                    }
                )
                
                # Executa workflow
                task_id = await workflow_manager.execute_workflow(workflow)
                result = await workflow_manager.get_workflow_status(task_id)
                
                return {
                    'status': 'success',
                    'images': result['images'],
                    'metadata': {
                        'workflow': request.workflow,
                        'task_id': task_id,
                        'parameters': workflow['parameters']
                    }
                }
                
            # Geração direta com SDXL
            else:
                # Aplica LoRAs se necessário
                if request.loras:
                    self.sdxl.model = await self.lora_manager.apply_loras(
                        self.sdxl.model,
                        request.loras
                    )
                    
                # Gera imagens
                images = await self.sdxl.generate(
                    prompt=request.prompt,
                    negative_prompt=request.negative_prompt,
                    width=request.width,
                    height=request.height,
                    num_inference_steps=request.num_inference_steps,
                    guidance_scale=request.guidance_scale,
                    batch_size=request.batch_size,
                    seed=request.seed
                )
                
                return {
                    'status': 'success',
                    'images': images,
                    'metadata': {
                        'prompt': request.prompt,
                        'negative_prompt': request.negative_prompt,
                        'parameters': {
                            'width': request.width,
                            'height': request.height,
                            'steps': request.num_inference_steps,
                            'cfg': request.guidance_scale,
                            'seed': request.seed
                        },
                        'loras': request.loras
                    }
                }
                
        except Exception as e:
            logger.error(f"Erro no pipeline: {e}")
            raise PipelineError(f"Falha no pipeline: {e}")
            
    def _update_memory_stats(self):
        """Atualiza estatísticas de uso de memória."""
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                memory = torch.cuda.memory_allocated(i)
                GPU_MEMORY.labels(i).set(memory)
                
    async def get_available_workflows(self) -> List[Dict]:
        """
        Lista workflows disponíveis.
        
        Returns:
            Lista de informações dos workflows
        """
        try:
            templates = await workflow_manager.list_templates()
            return [
                {
                    'name': t.name,
                    'description': t.description,
                    'category': t.category,
                    'metadata': t.metadata
                }
                for t in templates
            ]
        except Exception as e:
            logger.error(f"Erro listando workflows: {e}")
            return []
            
    async def get_available_loras(self) -> List[Dict]:
        """
        Lista LoRAs disponíveis.
        
        Returns:
            Lista de informações das LoRAs
        """
        try:
            return self.lora_manager.list_loras()
        except Exception as e:
            logger.error(f"Erro listando LoRAs: {e}")
            return []
            
    def cleanup(self):
        """Limpa recursos do pipeline."""
        try:
            # Descarrega LoRAs
            self.lora_manager.clear_loaded_loras()
            
            # Limpa cache de workflows
            workflow_manager.cache.clear()
            
            # Força coleta de lixo
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            logger.info("Pipeline limpo com sucesso")
            
        except Exception as e:
            logger.error(f"Erro na limpeza do pipeline: {e}")
            
# Instância global do pipeline
pipeline = ImagePipeline() 