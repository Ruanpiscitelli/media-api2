"""
Módulo para geração de thumbnails de vídeo usando FFmpeg.
"""

import os
import asyncio
from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager

from src.core.gpu.manager import GPUManager
from src.core.exceptions import NoGPUAvailableError

class ThumbnailGenerator:
    """
    Gerador de thumbnails para vídeos usando FFmpeg.
    Suporta geração de thumbnails estáticos e animados (GIF).
    """
    
    def __init__(self, gpu_manager: GPUManager, output_dir: str = "media/thumbnails"):
        """
        Inicializa o gerador de thumbnails.
        
        Args:
            gpu_manager: Gerenciador de GPUs para alocação de recursos
            output_dir: Diretório para salvar os thumbnails gerados
        """
        self.gpu_manager = gpu_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    @asynccontextmanager
    async def _allocate_gpu(self):
        """
        Context manager para alocação segura de GPU.
        Garante que o recurso seja liberado após o uso.
        """
        gpu_id = await self.gpu_manager.allocate_gpu(task_type="thumbnail")
        if not gpu_id:
            raise NoGPUAvailableError("No GPUs available for thumbnail generation")
        try:
            yield gpu_id
        finally:
            await self.gpu_manager.release_gpu(gpu_id)
        
    async def generate_static(
        self,
        video_path: str,
        timestamp: Optional[float] = None,
        width: int = 512,
        quality: int = 90
    ) -> str:
        """
        Gera um thumbnail estático do vídeo.
        
        Args:
            video_path: Caminho do vídeo fonte
            timestamp: Momento do vídeo para capturar (em segundos)
            width: Largura do thumbnail (altura é calculada mantendo aspect ratio)
            quality: Qualidade da imagem (1-100)
            
        Returns:
            str: Caminho do thumbnail gerado
        """
        video_id = Path(video_path).stem
        output_path = str(self.output_dir / f"{video_id}_thumb.jpg")
        
        # Se timestamp não for especificado, usa 10% da duração do vídeo
        if timestamp is None:
            duration_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {video_path}"
            duration = float((await asyncio.create_subprocess_shell(
                duration_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )).communicate()[0])
            timestamp = duration * 0.1
            
        async with self._allocate_gpu() as gpu_id:
            cmd = (
                f"ffmpeg -hwaccel cuda -hwaccel_device {gpu_id} -y "
                f"-ss {timestamp} -i {video_path} "
                f"-vf scale={width}:-1 -vframes 1 "
                f"-q:v {int((100-quality)/10)} {output_path}"
            )
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
        
        return output_path
        
    async def generate_animated(
        self,
        video_path: str,
        duration: float = 3.0,
        fps: int = 10,
        width: int = 512
    ) -> str:
        """
        Gera um thumbnail animado (GIF) do vídeo.
        
        Args:
            video_path: Caminho do vídeo fonte
            duration: Duração do GIF em segundos
            fps: Frames por segundo do GIF
            width: Largura do GIF (altura é calculada mantendo aspect ratio)
            
        Returns:
            str: Caminho do GIF gerado
        """
        video_id = Path(video_path).stem
        output_path = str(self.output_dir / f"{video_id}_preview.gif")
        
        # Calcula o início do trecho (20% da duração do vídeo)
        duration_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {video_path}"
        total_duration = float((await asyncio.create_subprocess_shell(
            duration_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )).communicate()[0])
        start_time = total_duration * 0.2
        
        async with self._allocate_gpu() as gpu_id:
            # Gera paleta otimizada para melhor qualidade
            palette_path = str(self.output_dir / f"{video_id}_palette.png")
            palette_cmd = (
                f"ffmpeg -hwaccel cuda -hwaccel_device {gpu_id} -y "
                f"-ss {start_time} -t {duration} -i {video_path} "
                f"-vf 'fps={fps},scale={width}:-1:flags=lanczos,palettegen' "
                f"{palette_path}"
            )
            
            process = await asyncio.create_subprocess_shell(
                palette_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            # Gera o GIF usando a paleta
            gif_cmd = (
                f"ffmpeg -hwaccel cuda -hwaccel_device {gpu_id} -y "
                f"-ss {start_time} -t {duration} -i {video_path} -i {palette_path} "
                f"-filter_complex 'fps={fps},scale={width}:-1:flags=lanczos[x];[x][1:v]paletteuse' "
                f"{output_path}"
            )
            
            process = await asyncio.create_subprocess_shell(
                gif_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
        
        # Remove a paleta temporária
        os.remove(palette_path)
        
        return output_path 