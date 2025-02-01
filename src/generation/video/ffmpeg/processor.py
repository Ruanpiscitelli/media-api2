"""
Processador FFmpeg para composição de vídeos.
Responsável por combinar frames, áudio e legendas em vídeos finais.
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
import torch
import torchvision
from prometheus_client import Summary

from src.core.config import settings
from src.core.exceptions import VideoCompositionError

logger = logging.getLogger(__name__)

# Métricas Prometheus
COMPOSITION_TIME = Summary(
    'video_composition_seconds',
    'Time spent composing video with FFmpeg'
)

class FFmpegProcessor:
    """
    Processador FFmpeg para composição de vídeos.
    Implementa composição otimizada com hardware acceleration.
    """
    
    def __init__(self, temp_dir: str = "temp/ffmpeg"):
        """
        Inicializa o processador FFmpeg.
        
        Args:
            temp_dir: Diretório para arquivos temporários
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
    @COMPOSITION_TIME.time()
    async def compose_video(
        self,
        frames: List[torch.Tensor],
        audio_path: Optional[str] = None,
        subtitles: Optional[str] = None,
        output_path: str = "output.mp4",
        fps: int = 30,
        codec: str = "h264",
        crf: int = 22,
        preset: str = "slow"
    ) -> str:
        """
        Compõe o vídeo final com áudio e legendas.
        
        Args:
            frames: Lista de frames do vídeo
            audio_path: Caminho do arquivo de áudio
            subtitles: Caminho do arquivo de legendas
            output_path: Caminho para salvar o vídeo
            fps: Frames por segundo
            codec: Codec de vídeo
            crf: Fator de qualidade (0-51, menor = melhor)
            preset: Preset de codificação
            
        Returns:
            Caminho do vídeo gerado
        """
        try:
            # Salva frames temporariamente
            frame_paths = await self._save_frames(frames)
            
            # Constrói comando FFmpeg
            cmd = self._build_ffmpeg_command(
                frame_paths=frame_paths,
                audio_path=audio_path,
                subtitles=subtitles,
                output_path=output_path,
                fps=fps,
                codec=codec,
                crf=crf,
                preset=preset
            )
            
            # Executa FFmpeg
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise VideoCompositionError(
                    f"Erro FFmpeg: {stderr.decode()}"
                )
                
            # Limpa arquivos temporários
            await self._cleanup(frame_paths)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Erro na composição do vídeo: {e}")
            raise VideoCompositionError(f"Falha na composição: {e}")
            
    async def _save_frames(
        self,
        frames: List[torch.Tensor]
    ) -> List[str]:
        """
        Salva frames em arquivos temporários.
        
        Args:
            frames: Lista de frames para salvar
            
        Returns:
            Lista de caminhos dos frames
        """
        try:
            frame_paths = []
            
            for i, frame in enumerate(frames):
                path = self.temp_dir / f"frame_{i:09d}.png"
                torchvision.utils.save_image(frame, path)
                frame_paths.append(str(path))
                
            return frame_paths
            
        except Exception as e:
            logger.error(f"Erro salvando frames: {e}")
            raise VideoCompositionError(f"Falha ao salvar frames: {e}")
            
    def _build_ffmpeg_command(
        self,
        frame_paths: List[str],
        audio_path: Optional[str],
        subtitles: Optional[str],
        output_path: str,
        fps: int,
        codec: str,
        crf: int,
        preset: str
    ) -> List[str]:
        """
        Constrói comando FFmpeg com todas as opções necessárias.
        
        Args:
            frame_paths: Lista de caminhos dos frames
            audio_path: Caminho do arquivo de áudio
            subtitles: Caminho do arquivo de legendas
            output_path: Caminho para salvar o vídeo
            fps: Frames por segundo
            codec: Codec de vídeo
            crf: Fator de qualidade
            preset: Preset de codificação
            
        Returns:
            Lista com partes do comando FFmpeg
        """
        try:
            cmd = [
                'ffmpeg',
                '-y',  # Sobrescreve arquivo de saída
                '-framerate', str(fps),
                '-i', f"{self.temp_dir}/frame_%09d.png"
            ]
            
            # Adiciona áudio se fornecido
            if audio_path:
                cmd.extend([
                    '-i', audio_path,
                    '-c:a', 'aac',
                    '-b:a', '192k'
                ])
                
            # Configurações de vídeo
            cmd.extend([
                '-c:v', codec,
                '-preset', preset,
                '-crf', str(crf),
                '-pix_fmt', 'yuv420p'
            ])
            
            # Habilita CUDA se disponível
            if torch.cuda.is_available():
                cmd.extend(['-hwaccel', 'cuda'])
                
            # Adiciona legendas se fornecidas
            if subtitles:
                cmd.extend([
                    '-vf',
                    f"subtitles={subtitles}:force_style='FontSize=24,Alignment=2'"
                ])
                
            # Configurações de threading
            cmd.extend([
                '-threads', '0',  # Usa todos os threads disponíveis
                '-movflags', '+faststart'  # Otimiza para streaming
            ])
            
            cmd.append(output_path)
            return cmd
            
        except Exception as e:
            logger.error(f"Erro construindo comando FFmpeg: {e}")
            raise VideoCompositionError(f"Falha no comando FFmpeg: {e}")
            
    async def _cleanup(self, frame_paths: List[str]):
        """
        Limpa arquivos temporários.
        
        Args:
            frame_paths: Lista de caminhos para limpar
        """
        try:
            for path in frame_paths:
                Path(path).unlink()
                
        except Exception as e:
            logger.warning(f"Erro limpando arquivos temporários: {e}")
            
    async def create_preview(
        self,
        video_path: str,
        output_path: str,
        duration: float = 3.0,
        resolution: Optional[tuple] = None
    ) -> str:
        """
        Cria um preview do vídeo.
        
        Args:
            video_path: Caminho do vídeo original
            output_path: Caminho para salvar o preview
            duration: Duração do preview em segundos
            resolution: Resolução opcional (largura, altura)
            
        Returns:
            Caminho do preview gerado
        """
        try:
            cmd = [
                'ffmpeg',
                '-y',
                '-i', video_path,
                '-t', str(duration),
                '-c:v', 'libx264',
                '-crf', '23',
                '-preset', 'fast'
            ]
            
            if resolution:
                cmd.extend([
                    '-vf',
                    f'scale={resolution[0]}:{resolution[1]}'
                ])
                
            cmd.append(output_path)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise VideoCompositionError(
                    f"Erro criando preview: {stderr.decode()}"
                )
                
            return output_path
            
        except Exception as e:
            logger.error(f"Erro criando preview: {e}")
            raise VideoCompositionError(f"Falha no preview: {e}")
            
    async def extract_frame(
        self,
        video_path: str,
        output_path: str,
        timestamp: float = 0.0,
        resolution: Optional[tuple] = None
    ) -> str:
        """
        Extrai um frame do vídeo.
        
        Args:
            video_path: Caminho do vídeo
            output_path: Caminho para salvar o frame
            timestamp: Momento do frame em segundos
            resolution: Resolução opcional (largura, altura)
            
        Returns:
            Caminho do frame extraído
        """
        try:
            cmd = [
                'ffmpeg',
                '-y',
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2'
            ]
            
            if resolution:
                cmd.extend([
                    '-vf',
                    f'scale={resolution[0]}:{resolution[1]}'
                ])
                
            cmd.append(output_path)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise VideoCompositionError(
                    f"Erro extraindo frame: {stderr.decode()}"
                )
                
            return output_path
            
        except Exception as e:
            logger.error(f"Erro extraindo frame: {e}")
            raise VideoCompositionError(f"Falha na extração: {e}")
            
# Instância global do processador
ffmpeg_processor = FFmpegProcessor() 