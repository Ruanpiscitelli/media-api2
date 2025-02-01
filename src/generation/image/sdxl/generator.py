"""
Gerador de imagens usando Stable Diffusion XL.
Otimizado para execução multi-GPU com gerenciamento eficiente de memória.
"""

import logging
from typing import List, Dict, Optional
import torch
from diffusers import StableDiffusionXLPipeline
from prometheus_client import Summary, Gauge

from src.core.config import settings
from src.core.exceptions import GenerationError

logger = logging.getLogger(__name__)

# Métricas Prometheus
GENERATION_TIME = Summary(
    'sdxl_generation_seconds',
    'Time spent generating images with SDXL'
)

GPU_MEMORY = Gauge(
    'sdxl_gpu_memory_bytes',
    'GPU memory usage for SDXL',
    ['device_id']
)

class SDXLGenerator:
    """
    Gerador de imagens usando SDXL com otimizações para multi-GPU.
    Implementa carregamento em baixa precisão e offload para CPU.
    """
    
    def __init__(self, model_path: str = None, device: str = "cuda"):
        """
        Inicializa o gerador SDXL.
        
        Args:
            model_path: Caminho para o modelo SDXL
            device: Dispositivo para inferência ('cuda' ou 'cpu')
        """
        self.model_path = model_path or settings.SDXL_MODEL_PATH
        self.device = device
        self.model = self._load_model()
        self.vae = self._load_vae()
        self.pipeline = self._setup_pipeline()
        
    def _load_model(self) -> StableDiffusionXLPipeline:
        """
        Carrega o modelo SDXL com otimizações de memória.
        """
        try:
            logger.info(f"Carregando modelo SDXL de {self.model_path}")
            
            model = StableDiffusionXLPipeline.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16,
                variant="fp16",
                use_safetensors=True
            )
            
            # Otimizações de memória
            model.enable_model_cpu_offload()
            model.enable_vae_slicing()
            
            return model
            
        except Exception as e:
            logger.error(f"Erro carregando modelo SDXL: {e}")
            raise GenerationError(f"Falha ao carregar modelo: {e}")
            
    def _load_vae(self):
        """
        Carrega o VAE otimizado.
        """
        try:
            vae = self.model.vae
            
            # Otimizações para o VAE
            if self.device == "cuda":
                vae.enable_slicing()
                vae.enable_tiling()
                
            return vae
            
        except Exception as e:
            logger.error(f"Erro carregando VAE: {e}")
            raise GenerationError(f"Falha ao carregar VAE: {e}")
            
    def _setup_pipeline(self) -> StableDiffusionXLPipeline:
        """
        Configura o pipeline com otimizações.
        """
        try:
            pipeline = StableDiffusionXLPipeline(
                vae=self.vae,
                text_encoder=self.model.text_encoder,
                tokenizer=self.model.tokenizer,
                unet=self.model.unet,
                scheduler=self.model.scheduler
            )
            
            # Otimizações de performance
            if self.device == "cuda":
                pipeline.enable_xformers_memory_efficient_attention()
                pipeline.enable_sequential_cpu_offload()
                
            return pipeline
            
        except Exception as e:
            logger.error(f"Erro configurando pipeline: {e}")
            raise GenerationError(f"Falha na configuração: {e}")
            
    @GENERATION_TIME.time()
    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        batch_size: int = 1,
        seed: Optional[int] = None
    ) -> List[torch.Tensor]:
        """
        Gera imagens usando o modelo SDXL.
        
        Args:
            prompt: Prompt positivo
            negative_prompt: Prompt negativo
            width: Largura da imagem
            height: Altura da imagem
            num_inference_steps: Número de passos de inferência
            guidance_scale: Escala de guidance do modelo
            batch_size: Número de imagens a gerar
            seed: Seed para geração determinística
            
        Returns:
            Lista de tensores com as imagens geradas
        """
        try:
            # Configura seed se fornecida
            if seed is not None:
                torch.manual_seed(seed)
                
            # Registra uso de memória
            if self.device == "cuda":
                for i in range(torch.cuda.device_count()):
                    memory = torch.cuda.memory_allocated(i)
                    GPU_MEMORY.labels(i).set(memory)
                    
            # Gera imagens
            with torch.cuda.amp.autocast():
                output = self.pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    num_images_per_prompt=batch_size
                )
                
            return output.images
            
        except Exception as e:
            logger.error(f"Erro na geração: {e}")
            raise GenerationError(f"Falha na geração: {e}")
            
    def update_memory_stats(self):
        """
        Atualiza estatísticas de uso de memória.
        """
        if self.device == "cuda":
            for i in range(torch.cuda.device_count()):
                memory = torch.cuda.memory_allocated(i)
                GPU_MEMORY.labels(i).set(memory) 