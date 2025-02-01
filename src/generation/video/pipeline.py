"""
Pipeline completo de geração de vídeos.
Integra FastHuayuan, FFmpeg e sistema de voz.
"""

import logging
import os
from typing import Dict, List, Optional, Tuple
import torch
from prometheus_client import Summary, Histogram, Gauge

from src.core.config import settings
from src.core.exceptions import VideoGenerationError
from .fast_huayuan.generator import VideoGenerator
from .ffmpeg.processor import ffmpeg_processor
from src.generation.speech.pipeline import speech_pipeline

logger = logging.getLogger(__name__)

# Métricas Prometheus
PIPELINE_TIME = Summary(
    'video_pipeline_seconds',
    'Time spent in video generation pipeline'
)

VIDEO_LENGTH = Histogram(
    'video_length_seconds',
    'Distribution of video lengths',
    buckets=(1, 3, 5, 10, 15, 30, 60)
)

GPU_MEMORY = Gauge(
    'video_pipeline_memory_bytes',
    'GPU memory usage in video pipeline',
    ['device_id']
)

class VideoRequest:
    """Modelo para requisição de geração de vídeo."""
    def __init__(
        self,
        prompt: str,
        duration: float = 5.0,
        fps: int = 30,
        resolution: Tuple[int, int] = (1024, 1024),
        motion_scale: float = 1.0,
        narration: Optional[str] = None,
        voice_id: Optional[str] = None,
        language: Optional[str] = None,
        audio_effects: Optional[Dict] = None,
        output_format: str = "mp4",
        seed: Optional[int] = None
    ):
        self.prompt = prompt
        self.duration = min(duration, 30.0)  # Limita a 30 segundos
        self.fps = min(fps, 60)  # Limita a 60fps
        self.resolution = (
            min(resolution[0], 2048),
            min(resolution[1], 2048)
        )  # Limita resolução
        self.motion_scale = motion_scale
        self.narration = narration
        self.voice_id = voice_id
        self.language = language
        self.audio_effects = audio_effects
        self.output_format = output_format
        self.seed = seed
        
class VideoPipeline:
    """
    Pipeline completo para geração de vídeos.
    Integra geração de frames, áudio e composição.
    """
    
    def __init__(self):
        """Inicializa o pipeline com todos os componentes."""
        self.video_generator = VideoGenerator()
        
    @PIPELINE_TIME.time()
    async def generate(self, request: VideoRequest) -> Dict:
        """
        Pipeline completo de geração de vídeo.
        
        Args:
            request: Requisição de geração
            
        Returns:
            Dicionário com resultados e metadados
        """
        try:
            # Registra métricas
            VIDEO_LENGTH.observe(request.duration)
            self._update_memory_stats()
            
            # Gera narração se solicitada
            audio_path = None
            if request.narration:
                audio_result = await speech_pipeline.generate_speech({
                    'text': request.narration,
                    'voice_id': request.voice_id,
                    'language': request.language,
                    'audio_effects': request.audio_effects
                })
                audio_path = audio_result['audio_path']
                
            # Gera frames do vídeo
            frames = await self.video_generator.generate_video(
                prompt=request.prompt,
                duration=request.duration,
                fps=request.fps,
                resolution=request.resolution,
                motion_scale=request.motion_scale,
                seed=request.seed
            )
            
            # Cria arquivo de legendas se necessário
            subtitle_path = None
            if request.narration:
                subtitle_path = await self._create_subtitles(
                    text=request.narration,
                    duration=request.duration
                )
                
            # Define caminho de saída
            output_dir = Path("outputs/videos")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"video_{uuid.uuid4()}.{request.output_format}"
            
            # Compõe vídeo final
            video_path = await ffmpeg_processor.compose_video(
                frames=frames,
                audio_path=audio_path,
                subtitles=subtitle_path,
                output_path=str(output_path),
                fps=request.fps
            )
            
            # Gera preview
            preview_path = None
            if os.path.exists(video_path):
                preview_path = await self._generate_preview(video_path)
                
            return {
                'status': 'success',
                'video_path': video_path,
                'preview_path': preview_path,
                'metadata': {
                    'duration': request.duration,
                    'fps': request.fps,
                    'resolution': request.resolution,
                    'has_audio': audio_path is not None,
                    'has_subtitles': subtitle_path is not None,
                    'prompt': request.prompt
                }
            }
            
        except Exception as e:
            logger.error(f"Erro no pipeline: {e}")
            raise VideoGenerationError(f"Falha no pipeline: {e}")
            
    async def _create_subtitles(
        self,
        text: str,
        duration: float
    ) -> Optional[str]:
        """
        Cria arquivo de legendas.
        
        Args:
            text: Texto da narração
            duration: Duração do vídeo
            
        Returns:
            Caminho do arquivo de legendas
        """
        try:
            subtitle_dir = Path("temp/subtitles")
            subtitle_dir.mkdir(parents=True, exist_ok=True)
            
            subtitle_path = subtitle_dir / f"subs_{uuid.uuid4()}.srt"
            
            # Cria legenda simples
            with open(subtitle_path, 'w') as f:
                f.write("1\n")
                f.write("00:00:00,000 --> ")
                
                # Formata tempo final
                hours = int(duration // 3600)
                minutes = int((duration % 3600) // 60)
                seconds = int(duration % 60)
                ms = int((duration % 1) * 1000)
                
                f.write(f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}\n")
                f.write(text + "\n")
                
            return str(subtitle_path)
            
        except Exception as e:
            logger.error(f"Erro criando legendas: {e}")
            return None
            
    async def _generate_preview(
        self,
        video_path: str,
        duration: float = 3.0
    ) -> Optional[str]:
        """
        Gera um preview do vídeo.
        
        Args:
            video_path: Caminho do vídeo original
            duration: Duração do preview
            
        Returns:
            Caminho do preview
        """
        try:
            preview_dir = Path("outputs/previews")
            preview_dir.mkdir(parents=True, exist_ok=True)
            
            preview_path = preview_dir / f"preview_{uuid.uuid4()}.mp4"
            
            await ffmpeg_processor.create_preview(
                video_path=video_path,
                output_path=str(preview_path),
                duration=duration,
                resolution=(512, 512)
            )
            
            return str(preview_path)
            
        except Exception as e:
            logger.error(f"Erro gerando preview: {e}")
            return None
            
    def _update_memory_stats(self):
        """Atualiza estatísticas de uso de memória."""
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                memory = torch.cuda.memory_allocated(i)
                GPU_MEMORY.labels(i).set(memory)
                
    async def cleanup(self):
        """Limpa recursos do pipeline."""
        try:
            # Limpa diretórios temporários
            temp_dirs = [
                Path("temp/ffmpeg"),
                Path("temp/subtitles")
            ]
            
            for dir_path in temp_dirs:
                if dir_path.exists():
                    for file in dir_path.glob("*"):
                        file.unlink()
                        
            # Força coleta de lixo
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            logger.info("Pipeline limpo com sucesso")
            
        except Exception as e:
            logger.error(f"Erro na limpeza do pipeline: {e}")
            
# Instância global do pipeline
pipeline = VideoPipeline() 