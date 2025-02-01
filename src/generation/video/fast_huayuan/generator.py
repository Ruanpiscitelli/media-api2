"""
Gerador de vídeos usando FastHuayuan.
Otimizado para execução multi-GPU com gerenciamento eficiente de memória.
"""

import logging
from typing import Dict, List, Optional, Tuple
import torch
from torch import nn
import numpy as np
from prometheus_client import Summary, Gauge
from collections import deque

from src.core.config import settings
from src.core.exceptions import VideoGenerationError

logger = logging.getLogger(__name__)

# Métricas Prometheus
GENERATION_TIME = Summary(
    'video_generation_seconds',
    'Time spent generating video frames'
)

FRAME_TIME = Summary(
    'frame_generation_seconds',
    'Time spent generating individual frames'
)

GPU_MEMORY = Gauge(
    'video_gpu_memory_bytes',
    'GPU memory usage for video generation',
    ['device_id']
)

class FrameBuffer:
    """Buffer para gerenciamento de frames em memória."""
    
    def __init__(self, max_size: int = 300):
        """
        Inicializa o buffer de frames.
        
        Args:
            max_size: Tamanho máximo do buffer (em frames)
        """
        self.buffer = deque(maxlen=max_size)
        self.max_memory = 8 * 1024 * 1024 * 1024  # 8GB
        
    def add_frame(self, frame: torch.Tensor):
        """Adiciona um frame ao buffer."""
        self.buffer.append(frame)
        self._manage_memory()
        
    def get_frames(self) -> List[torch.Tensor]:
        """Retorna todos os frames no buffer."""
        return list(self.buffer)
        
    def _manage_memory(self):
        """Gerencia o uso de memória do buffer."""
        current_memory = sum(
            frame.element_size() * frame.nelement()
            for frame in self.buffer
        )
        
        while current_memory > self.max_memory and self.buffer:
            self.buffer.popleft()
            current_memory = sum(
                frame.element_size() * frame.nelement()
                for frame in self.buffer
            )

class VideoGenerator:
    """
    Gerador de vídeos usando FastHuayuan.
    Implementa geração otimizada de frames e interpolação.
    """
    
    def __init__(
        self,
        model_path: str = None,
        device: str = "cuda",
        frame_buffer_size: int = 300
    ):
        """
        Inicializa o gerador de vídeos.
        
        Args:
            model_path: Caminho para o modelo FastHuayuan
            device: Dispositivo para inferência ('cuda' ou 'cpu')
            frame_buffer_size: Tamanho do buffer de frames
        """
        self.model_path = model_path or settings.FAST_HUAYUAN_MODEL_PATH
        self.device = device
        self.model = self._load_model()
        self.frame_buffer = FrameBuffer(max_size=frame_buffer_size)
        
    def _load_model(self) -> nn.Module:
        """
        Carrega o modelo FastHuayuan com otimizações.
        """
        try:
            logger.info(f"Carregando modelo FastHuayuan de {self.model_path}")
            
            model = FastHuayuanModel.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16,
                variant="fp16"
            )
            
            # Otimizações de memória
            if self.device == "cuda":
                model.enable_model_cpu_offload()
                model.enable_vae_slicing()
                
            return model
            
        except Exception as e:
            logger.error(f"Erro carregando modelo FastHuayuan: {e}")
            raise VideoGenerationError(f"Falha ao carregar modelo: {e}")
            
    @GENERATION_TIME.time()
    async def generate_video(
        self,
        prompt: str,
        duration: float = 5.0,
        fps: int = 30,
        resolution: Tuple[int, int] = (1024, 1024),
        motion_scale: float = 1.0,
        seed: Optional[int] = None
    ) -> List[torch.Tensor]:
        """
        Gera uma sequência de frames para o vídeo.
        
        Args:
            prompt: Descrição do vídeo
            duration: Duração em segundos
            fps: Frames por segundo
            resolution: Resolução do vídeo (largura, altura)
            motion_scale: Escala de movimento (1.0 = normal)
            seed: Seed para geração determinística
            
        Returns:
            Lista de frames do vídeo
        """
        try:
            # Configura seed se fornecida
            if seed is not None:
                torch.manual_seed(seed)
                
            num_frames = int(duration * fps)
            
            # Gera keyframes
            keyframes = await self._generate_keyframes(
                prompt=prompt,
                num_keyframes=4,
                resolution=resolution
            )
            
            # Interpola entre keyframes
            frames = []
            for i in range(len(keyframes) - 1):
                interpolated = await self._interpolate_frames(
                    keyframes[i],
                    keyframes[i + 1],
                    num_intermediate=num_frames // 4,
                    motion_scale=motion_scale
                )
                frames.extend(interpolated)
                
            # Ajusta número de frames se necessário
            if len(frames) > num_frames:
                frames = frames[:num_frames]
            elif len(frames) < num_frames:
                # Repete último frame
                frames.extend([frames[-1]] * (num_frames - len(frames)))
                
            return frames
            
        except Exception as e:
            logger.error(f"Erro na geração de vídeo: {e}")
            raise VideoGenerationError(f"Falha na geração: {e}")
            
    @FRAME_TIME.time()
    async def _generate_keyframes(
        self,
        prompt: str,
        num_keyframes: int,
        resolution: Tuple[int, int]
    ) -> List[torch.Tensor]:
        """
        Gera keyframes para o vídeo.
        
        Args:
            prompt: Descrição do vídeo
            num_keyframes: Número de keyframes
            resolution: Resolução dos frames
            
        Returns:
            Lista de keyframes
        """
        try:
            keyframes = []
            
            # Registra uso de memória
            if self.device == "cuda":
                for i in range(torch.cuda.device_count()):
                    memory = torch.cuda.memory_allocated(i)
                    GPU_MEMORY.labels(i).set(memory)
                    
            # Gera cada keyframe
            with torch.cuda.amp.autocast():
                for i in range(num_keyframes):
                    frame = self.model.generate(
                        prompt=prompt,
                        width=resolution[0],
                        height=resolution[1],
                        num_inference_steps=30,
                        guidance_scale=7.5
                    )
                    keyframes.append(frame)
                    
            return keyframes
            
        except Exception as e:
            logger.error(f"Erro gerando keyframes: {e}")
            raise VideoGenerationError(f"Falha nos keyframes: {e}")
            
    async def _interpolate_frames(
        self,
        frame1: torch.Tensor,
        frame2: torch.Tensor,
        num_intermediate: int,
        motion_scale: float = 1.0
    ) -> List[torch.Tensor]:
        """
        Interpola frames intermediários.
        
        Args:
            frame1: Frame inicial
            frame2: Frame final
            num_intermediate: Número de frames intermediários
            motion_scale: Escala de movimento
            
        Returns:
            Lista de frames interpolados
        """
        try:
            frames = []
            
            # Calcula fluxo óptico
            flow = self.model.estimate_flow(frame1, frame2)
            flow = flow * motion_scale
            
            # Gera frames intermediários
            for i in range(num_intermediate):
                t = (i + 1) / (num_intermediate + 1)
                
                # Interpola com fluxo óptico
                warped = self.model.warp_frame(
                    frame1,
                    flow * t
                )
                
                # Refina frame
                refined = self.model.refine_frame(
                    warped,
                    frame1,
                    frame2,
                    t
                )
                
                frames.append(refined)
                
            return frames
            
        except Exception as e:
            logger.error(f"Erro na interpolação: {e}")
            raise VideoGenerationError(f"Falha na interpolação: {e}")
            
    def update_memory_stats(self):
        """Atualiza estatísticas de uso de memória."""
        if self.device == "cuda":
            for i in range(torch.cuda.device_count()):
                memory = torch.cuda.memory_allocated(i)
                GPU_MEMORY.labels(i).set(memory) 