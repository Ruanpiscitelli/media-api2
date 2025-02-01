"""
Motor de processamento de vídeo com suporte a composição, transições e efeitos.
Integra com FFmpeg e MoviePy para processamento avançado.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import torch
import cv2
from PIL import Image
import moviepy.editor as mpy
from moviepy.video.fx.all import *
import ffmpeg
import tempfile
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class VideoEngine:
    """
    Motor de processamento de vídeo com suporte a composição e efeitos.
    Integra FFmpeg e MoviePy para diferentes operações.
    """
    
    def __init__(self):
        """Inicializa o motor de vídeo."""
        self.device = None
        self.available_gpus = []
        self._setup_engines()
        
    def _setup_engines(self):
        """Configura os diferentes engines de processamento."""
        try:
            if torch.cuda.is_available():
                # Lista GPUs disponíveis
                self.available_gpus = list(range(torch.cuda.device_count()))
                if self.available_gpus:
                    self.device = torch.device(f"cuda:{self.available_gpus[0]}")
                    cv2.cuda.setDevice(self.available_gpus[0])
                else:
                    logger.warning("CUDA disponível mas nenhuma GPU encontrada")
                    self.device = torch.device("cpu")
            else:
                logger.info("CUDA não disponível, usando CPU")
                self.device = torch.device("cpu")
        except Exception as e:
            logger.error(f"Erro configurando engines: {e}")
            self.device = torch.device("cpu")
            
    @contextmanager
    def _gpu_memory_manager(self):
        """Gerencia alocação e liberação de memória GPU."""
        try:
            if self.device.type == "cuda":
                torch.cuda.empty_cache()
            yield
        finally:
            if self.device.type == "cuda":
                torch.cuda.empty_cache()
                
    def _check_gpu_memory(self, required_mb: int = 1000) -> bool:
        """
        Verifica se há memória GPU suficiente.
        
        Args:
            required_mb: Memória requerida em MB
            
        Returns:
            True se há memória suficiente
        """
        if self.device.type != "cuda":
            return False
            
        try:
            free_memory = (torch.cuda.get_device_properties(self.device).total_memory - 
                        torch.cuda.memory_allocated(self.device))
            return free_memory >= required_mb * 1024 * 1024
        except Exception as e:
            logger.error(f"Erro verificando memória GPU: {e}")
            return False
        
    async def create_scene(
        self,
        width: int,
        height: int,
        duration: float,
        fps: int = 30,
        background: Optional[Dict[str, Any]] = None
    ) -> mpy.VideoClip:
        """
        Cria uma nova cena de vídeo.
        
        Args:
            width: Largura do vídeo
            height: Altura do vídeo
            duration: Duração em segundos
            fps: Frames por segundo
            background: Configuração do fundo
            
        Returns:
            Clip de vídeo MoviePy
        """
        # Criar fundo
        if background:
            if background.get("type") == "color":
                color = background.get("color", (0, 0, 0))
                clip = mpy.ColorClip(
                    size=(width, height),
                    color=color,
                    duration=duration
                )
            elif background.get("type") == "image":
                image_path = background.get("image")
                clip = mpy.ImageClip(image_path).set_duration(duration)
                clip = clip.resize((width, height))
            elif background.get("type") == "video":
                video_path = background.get("video")
                clip = mpy.VideoFileClip(video_path)
                clip = clip.resize((width, height))
                if clip.duration > duration:
                    clip = clip.subclip(0, duration)
                else:
                    clip = clip.loop(duration=duration)
        else:
            # Fundo preto por padrão
            clip = mpy.ColorClip(
                size=(width, height),
                color=(0, 0, 0),
                duration=duration
            )
            
        return clip.set_fps(fps)
        
    async def add_element(
        self,
        clip: mpy.VideoClip,
        element: Dict[str, Any],
        start_time: float = 0
    ) -> mpy.VideoClip:
        """
        Adiciona um elemento à cena.
        
        Args:
            clip: Clip base
            element: Configuração do elemento
            start_time: Tempo inicial
            
        Returns:
            Clip com elemento adicionado
        """
        element_type = element.get("type")
        
        if element_type == "text":
            text_clip = await self._create_text_element(
                element,
                clip.size
            )
        elif element_type == "image":
            text_clip = await self._create_image_element(
                element,
                clip.size
            )
        elif element_type == "shape":
            text_clip = await self._create_shape_element(
                element,
                clip.size
            )
        else:
            raise ValueError(f"Tipo de elemento desconhecido: {element_type}")
            
        # Aplicar posição
        position = element.get("position", "center")
        if isinstance(position, (list, tuple)):
            pos = tuple(position)
        else:
            pos = position
            
        # Aplicar duração
        duration = element.get("duration", clip.duration)
        text_clip = text_clip.set_duration(duration)
        
        # Aplicar efeitos
        if "effects" in element:
            text_clip = await self._apply_effects(text_clip, element["effects"])
            
        # Compor com clip base
        return mpy.CompositeVideoClip([
            clip,
            text_clip.set_start(start_time).set_position(pos)
        ])
        
    async def apply_transition(
        self,
        clip1: mpy.VideoClip,
        clip2: mpy.VideoClip,
        transition: Dict[str, Any]
    ) -> mpy.VideoClip:
        """
        Aplica uma transição entre dois clips.
        
        Args:
            clip1: Primeiro clip
            clip2: Segundo clip
            transition: Configuração da transição
            
        Returns:
            Clip com transição aplicada
        """
        transition_type = transition.get("type", "fade")
        duration = transition.get("duration", 1.0)
        
        if transition_type == "fade":
            return mpy.concatenate_videoclips(
                [clip1, clip2],
                method="compose",
                padding=-duration
            )
        elif transition_type == "slide":
            direction = transition.get("direction", "left")
            return mpy.concatenate_videoclips(
                [clip1, clip2],
                method="compose",
                padding=-duration,
                transition=slide(duration, direction)
            )
        elif transition_type == "wipe":
            direction = transition.get("direction", "left")
            return mpy.concatenate_videoclips(
                [clip1, clip2],
                method="compose",
                padding=-duration,
                transition=wipe(duration, direction)
            )
        else:
            raise ValueError(f"Tipo de transição desconhecido: {transition_type}")
            
    async def render_video(
        self,
        clip: mpy.VideoClip,
        output_path: str,
        codec: str = "libx264",
        bitrate: str = "8000k",
        audio: bool = True,
        **kwargs
    ):
        """
        Renderiza um clip final para arquivo.
        
        Args:
            clip: Clip para renderizar
            output_path: Caminho do arquivo de saída
            codec: Codec de vídeo
            bitrate: Bitrate do vídeo
            audio: Se deve incluir áudio
            **kwargs: Argumentos adicionais para write_videofile
        """
        try:
            clip.write_videofile(
                output_path,
                codec=codec,
                bitrate=bitrate,
                audio=audio,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Erro renderizando vídeo: {e}")
            raise
            
    async def _create_text_element(
        self,
        config: Dict[str, Any],
        canvas_size: Tuple[int, int]
    ) -> mpy.VideoClip:
        """Cria um elemento de texto."""
        text = config.get("text", "")
        font = config.get("font", "Arial")
        size = config.get("size", 32)
        color = config.get("color", "white")
        
        return mpy.TextClip(
            text,
            fontsize=size,
            font=font,
            color=color
        )
        
    async def _create_image_element(
        self,
        config: Dict[str, Any],
        canvas_size: Tuple[int, int]
    ) -> mpy.VideoClip:
        """Cria um elemento de imagem."""
        image_path = config.get("image")
        if not image_path:
            raise ValueError("Caminho da imagem não especificado")
            
        clip = mpy.ImageClip(image_path)
        
        # Redimensionar se necessário
        if "dimensions" in config:
            width, height = config["dimensions"]
            clip = clip.resize((width, height))
            
        return clip
        
    async def _create_shape_element(
        self,
        config: Dict[str, Any],
        canvas_size: Tuple[int, int]
    ) -> mpy.VideoClip:
        """Cria um elemento de forma."""
        shape_type = config.get("shape", "rectangle")
        color = config.get("color", "white")
        dimensions = config.get("dimensions", canvas_size)
        
        if shape_type == "rectangle":
            return mpy.ColorClip(
                size=dimensions,
                color=color
            )
        elif shape_type == "circle":
            # TODO: Implementar círculo
            pass
        else:
            raise ValueError(f"Tipo de forma desconhecido: {shape_type}")
            
    async def _apply_effects(
        self,
        clip: mpy.VideoClip,
        effects: List[Dict[str, Any]]
    ) -> mpy.VideoClip:
        """Aplica efeitos a um clip."""
        for effect in effects:
            effect_type = effect.get("type")
            
            if effect_type == "fade_in":
                duration = effect.get("duration", 1.0)
                clip = clip.fadein(duration)
            elif effect_type == "fade_out":
                duration = effect.get("duration", 1.0)
                clip = clip.fadeout(duration)
            elif effect_type == "blur":
                sigma = effect.get("sigma", 5.0)
                clip = clip.fl_image(
                    lambda frame: cv2.GaussianBlur(
                        frame,
                        (0, 0),
                        sigma
                    )
                )
            elif effect_type == "rotate":
                angle = effect.get("angle", 0)
                clip = clip.rotate(angle)
                
        return clip

# Instância global do motor de vídeo
video_engine = VideoEngine() 