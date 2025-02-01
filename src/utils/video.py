"""
Processador de vídeo com funções utilitárias.
Implementa carregamento, processamento e salvamento de vídeos.
"""

import logging
import os
import tempfile
from typing import List, Dict, Optional, Union
import cv2
import numpy as np
import ffmpeg
import requests
from PIL import Image

from src.core.config import settings

logger = logging.getLogger(__name__)

class VideoProcessor:
    """
    Processador de vídeo com funções utilitárias.
    Implementa operações comuns de processamento.
    """
    
    def __init__(self):
        """Inicializa o processador."""
        self.temp_dir = tempfile.mkdtemp()
        
    async def load_video(
        self,
        path: str,
        position: Optional[Dict[str, float]] = None,
        style: Optional[Dict] = None
    ) -> Dict:
        """
        Carrega vídeo e aplica transformações.
        
        Args:
            path: Caminho do vídeo
            position: Posição do vídeo
            style: Estilos a aplicar
            
        Returns:
            Dicionário com vídeo processado
        """
        try:
            # Abre vídeo
            cap = cv2.VideoCapture(path)
            
            if not cap.isOpened():
                raise ValueError(f"Erro abrindo vídeo: {path}")
                
            # Lê primeiro frame
            ret, frame = cap.read()
            
            if not ret:
                raise ValueError(f"Erro lendo frame do vídeo: {path}")
                
            # Aplica transformações
            if style and 'size' in style:
                frame = cv2.resize(
                    frame,
                    (
                        int(style['size']['width']),
                        int(style['size']['height'])
                    )
                )
                
            cap.release()
            
            return {
                'type': 'video',
                'path': path,
                'image': frame,  # Primeiro frame para preview
                'position': position or {'x': 0, 'y': 0}
            }
            
        except Exception as e:
            logger.error(f"Erro carregando vídeo: {e}")
            raise
            
    async def load_image(
        self,
        path: str,
        position: Optional[Dict[str, float]] = None,
        style: Optional[Dict] = None
    ) -> Dict:
        """
        Carrega imagem e aplica transformações.
        
        Args:
            path: Caminho da imagem
            position: Posição da imagem
            style: Estilos a aplicar
            
        Returns:
            Dicionário com imagem processada
        """
        try:
            # Carrega imagem
            if path.startswith('http'):
                # Download de URL
                response = requests.get(path)
                response.raise_for_status()
                
                # Salva temporariamente
                temp_path = os.path.join(self.temp_dir, 'temp.jpg')
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                    
                img = cv2.imread(temp_path)
                os.remove(temp_path)
                
            else:
                img = cv2.imread(path)
                
            if img is None:
                raise ValueError(f"Erro carregando imagem: {path}")
                
            # Aplica transformações
            if style and 'size' in style:
                img = cv2.resize(
                    img,
                    (
                        int(style['size']['width']),
                        int(style['size']['height'])
                    )
                )
                
            return {
                'type': 'image',
                'image': img,
                'position': position or {'x': 0, 'y': 0}
            }
            
        except Exception as e:
            logger.error(f"Erro carregando imagem: {e}")
            raise
            
    async def extract_frame(
        self,
        path: str,
        time: float,
        position: Optional[Dict[str, float]] = None,
        style: Optional[Dict] = None
    ) -> Dict:
        """
        Extrai frame de um vídeo.
        
        Args:
            path: Caminho do vídeo
            time: Momento do vídeo em segundos
            position: Posição do frame
            style: Estilos a aplicar
            
        Returns:
            Dicionário com frame extraído
        """
        try:
            # Abre vídeo
            cap = cv2.VideoCapture(path)
            
            if not cap.isOpened():
                raise ValueError(f"Erro abrindo vídeo: {path}")
                
            # Posiciona no tempo correto
            cap.set(cv2.CAP_PROP_POS_MSEC, time * 1000)
            
            # Lê frame
            ret, frame = cap.read()
            
            if not ret:
                raise ValueError(f"Erro extraindo frame em {time}s")
                
            # Aplica transformações
            if style and 'size' in style:
                frame = cv2.resize(
                    frame,
                    (
                        int(style['size']['width']),
                        int(style['size']['height'])
                    )
                )
                
            cap.release()
            
            return {
                'type': 'image',
                'image': frame,
                'position': position or {'x': 0, 'y': 0}
            }
            
        except Exception as e:
            logger.error(f"Erro extraindo frame: {e}")
            raise
            
    async def frames_to_video(
        self,
        frames: List[np.ndarray],
        fps: int = 30,
        **kwargs
    ) -> str:
        """
        Converte frames para vídeo.
        
        Args:
            frames: Lista de frames
            fps: Frames por segundo
            **kwargs: Argumentos adicionais para ffmpeg
            
        Returns:
            Caminho do vídeo gerado
        """
        try:
            # Cria diretório temporário
            with tempfile.TemporaryDirectory() as temp_dir:
                # Salva frames como imagens
                frame_paths = []
                for i, frame in enumerate(frames):
                    path = os.path.join(temp_dir, f'frame_{i:04d}.png')
                    cv2.imwrite(path, frame)
                    frame_paths.append(path)
                    
                # Cria vídeo com ffmpeg
                output_path = os.path.join(temp_dir, 'output.mp4')
                
                stream = ffmpeg.input(
                    os.path.join(temp_dir, 'frame_%04d.png'),
                    pattern_type='sequence',
                    framerate=fps
                )
                
                stream = ffmpeg.output(
                    stream,
                    output_path,
                    vcodec='h264',
                    **kwargs
                )
                
                stream.overwrite_output().run(
                    capture_stdout=True,
                    capture_stderr=True
                )
                
                return output_path
                
        except Exception as e:
            logger.error(f"Erro convertendo frames para vídeo: {e}")
            raise
            
    async def download_audio(
        self,
        url: str,
        volume: float = 1.0
    ) -> str:
        """
        Baixa e processa áudio.
        
        Args:
            url: URL do áudio
            volume: Volume do áudio
            
        Returns:
            Caminho do áudio processado
        """
        try:
            # Download do áudio
            response = requests.get(url)
            response.raise_for_status()
            
            # Salva temporariamente
            input_path = os.path.join(self.temp_dir, 'input_audio')
            with open(input_path, 'wb') as f:
                f.write(response.content)
                
            # Processa com ffmpeg
            output_path = os.path.join(self.temp_dir, 'output_audio.wav')
            
            stream = ffmpeg.input(input_path)
            
            # Ajusta volume
            if volume != 1.0:
                stream = ffmpeg.filter(
                    stream,
                    'volume',
                    volume=volume
                )
                
            stream = ffmpeg.output(
                stream,
                output_path,
                acodec='pcm_s16le'
            )
            
            stream.overwrite_output().run(
                capture_stdout=True,
                capture_stderr=True
            )
            
            os.remove(input_path)
            return output_path
            
        except Exception as e:
            logger.error(f"Erro baixando áudio: {e}")
            raise
            
    async def mix_audio(
        self,
        audio_paths: List[str],
        volumes: Optional[List[float]] = None
    ) -> str:
        """
        Mixa múltiplos áudios.
        
        Args:
            audio_paths: Lista de caminhos de áudio
            volumes: Lista de volumes
            
        Returns:
            Caminho do áudio mixado
        """
        try:
            if not volumes:
                volumes = [1.0] * len(audio_paths)
                
            # Cria inputs
            inputs = []
            for path, volume in zip(audio_paths, volumes):
                stream = ffmpeg.input(path)
                
                if volume != 1.0:
                    stream = ffmpeg.filter(
                        stream,
                        'volume',
                        volume=volume
                    )
                    
                inputs.append(stream)
                
            # Mixa áudios
            output_path = os.path.join(self.temp_dir, 'mixed_audio.wav')
            
            stream = ffmpeg.filter(
                inputs,
                'amix',
                inputs=len(inputs)
            )
            
            stream = ffmpeg.output(
                stream,
                output_path,
                acodec='pcm_s16le'
            )
            
            stream.overwrite_output().run(
                capture_stdout=True,
                capture_stderr=True
            )
            
            return output_path
            
        except Exception as e:
            logger.error(f"Erro mixando áudios: {e}")
            raise
            
    def save_video(
        self,
        frames: List[np.ndarray],
        output_path: str,
        fps: int = 30
    ):
        """
        Salva frames como vídeo.
        
        Args:
            frames: Lista de frames
            output_path: Caminho de saída
            fps: Frames por segundo
        """
        try:
            if not frames:
                raise ValueError("Lista de frames vazia")
                
            # Configura writer
            height, width = frames[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(
                output_path,
                fourcc,
                fps,
                (width, height)
            )
            
            # Escreve frames
            for frame in frames:
                writer.write(frame)
                
            writer.release()
            
        except Exception as e:
            logger.error(f"Erro salvando vídeo: {e}")
            raise 