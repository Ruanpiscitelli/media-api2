"""
Sistema FFmpeg para processamento e composição de vídeo.
Responsável por gerenciar operações de vídeo usando FFmpeg.
"""

from typing import List, Dict, Optional, Union
from pathlib import Path
import asyncio
import json
import logging
from prometheus_client import Counter, Gauge, Summary

logger = logging.getLogger(__name__)

# Métricas Prometheus
VIDEO_PROCESSING_TIME = Summary('video_processing_seconds', 'Tempo de processamento de vídeo')
VIDEO_ERRORS = Counter('video_errors_total', 'Total de erros no processamento de vídeo')
ACTIVE_PROCESSES = Gauge('ffmpeg_active_processes', 'Processos FFmpeg ativos')

class VideoCreationError(Exception):
    """Exceção customizada para erros na criação de vídeos"""
    pass

class FFmpegError(Exception):
    """Exceção customizada para erros do FFmpeg"""
    pass

class FFmpegSystem:
    def __init__(self):
        """Inicializa o sistema FFmpeg com diretórios necessários"""
        self.temp_dir = Path("temp/ffmpeg")
        self.output_dir = Path("output/videos")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurações padrão
        self.default_video_settings = {
            'codec': 'libx264',
            'preset': 'slow',
            'crf': '23',
            'pixel_format': 'yuv420p'
        }
        
        self.default_audio_settings = {
            'codec': 'aac',
            'bitrate': '192k'
        }
        
    @VIDEO_PROCESSING_TIME.time()
    async def create_video(
        self,
        composition: Dict,
        output_path: str,
        format: str = "mp4"
    ) -> str:
        """
        Cria um vídeo baseado em uma composição JSON
        
        Args:
            composition: Dicionário com a composição do vídeo
            output_path: Caminho do arquivo de saída
            format: Formato do vídeo (mp4, webm, etc)
            
        Returns:
            str: Caminho do arquivo de vídeo gerado
        """
        try:
            ACTIVE_PROCESSES.inc()
            
            # Preparar recursos
            resources = await self._prepare_resources(composition)
            
            # Construir pipeline de processamento
            pipeline = await self._build_pipeline(composition, resources)
            
            # Executar FFmpeg
            output_file = await self._execute_pipeline(pipeline, output_path)
            
            return output_file
            
        except Exception as e:
            VIDEO_ERRORS.inc()
            logger.error(f"Erro na criação do vídeo: {e}")
            raise VideoCreationError(f"Falha na criação: {e}")
        finally:
            ACTIVE_PROCESSES.dec()

    async def _prepare_resources(self, composition: Dict) -> Dict:
        """
        Prepara todos os recursos necessários para o vídeo
        
        Args:
            composition: Dicionário com recursos a serem preparados
            
        Returns:
            Dict: Dicionário com caminhos dos recursos preparados
        """
        resources = {
            'images': await self._prepare_images(composition.get('images', [])),
            'audio': await self._prepare_audio(composition.get('audio', {})),
            'subtitles': await self._prepare_subtitles(composition.get('subtitles', {})),
            'overlays': await self._prepare_overlays(composition.get('overlays', []))
        }
        return resources
        
    async def _prepare_images(self, images: List[Dict]) -> List[str]:
        """Prepara imagens para o vídeo"""
        prepared_images = []
        for img in images:
            # Processar e otimizar imagem
            processed_path = await self._process_image(img)
            prepared_images.append(processed_path)
        return prepared_images
        
    async def _prepare_audio(self, audio: Dict) -> Optional[str]:
        """Prepara áudio para o vídeo"""
        if not audio:
            return None
            
        # Processar e normalizar áudio
        processed_path = await self._process_audio(audio)
        return processed_path
        
    async def _prepare_subtitles(self, subtitles: Dict) -> Optional[str]:
        """Prepara legendas para o vídeo"""
        if not subtitles:
            return None
            
        # Gerar arquivo SRT
        srt_path = await self._generate_srt(subtitles)
        return srt_path
        
    async def _prepare_overlays(self, overlays: List[Dict]) -> List[Dict]:
        """Prepara overlays para o vídeo"""
        prepared_overlays = []
        for overlay in overlays:
            # Processar overlay
            processed = await self._process_overlay(overlay)
            prepared_overlays.append(processed)
        return prepared_overlays
        
    async def _build_pipeline(self, composition: Dict, resources: Dict) -> List[str]:
        """
        Constrói o pipeline de processamento FFmpeg
        
        Args:
            composition: Configuração da composição
            resources: Recursos preparados
            
        Returns:
            List[str]: Comando FFmpeg construído
        """
        # Construir comando base
        cmd = ['ffmpeg', '-y']  # Sobrescrever arquivo se existir
        
        # Adicionar inputs
        for resource in resources['images']:
            cmd.extend(['-i', resource])
            
        if resources['audio']:
            cmd.extend(['-i', resources['audio']])
            
        # Adicionar filtros complexos
        filter_complex = self._build_filter_complex(composition, resources)
        if filter_complex:
            cmd.extend(['-filter_complex', filter_complex])
            
        # Configurações de output
        cmd.extend([
            '-c:v', self.default_video_settings['codec'],
            '-preset', self.default_video_settings['preset'],
            '-crf', self.default_video_settings['crf'],
            '-pix_fmt', self.default_video_settings['pixel_format']
        ])
        
        if resources['audio']:
            cmd.extend([
                '-c:a', self.default_audio_settings['codec'],
                '-b:a', self.default_audio_settings['bitrate']
            ])
            
        return cmd
        
    async def _execute_pipeline(self, cmd: List[str], output_path: str) -> str:
        """
        Executa o pipeline FFmpeg
        
        Args:
            cmd: Comando FFmpeg a ser executado
            output_path: Caminho do arquivo de saída
            
        Returns:
            str: Caminho do arquivo gerado
        """
        cmd.append(output_path)
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise FFmpegError(f"Erro no FFmpeg: {stderr.decode()}")
            
        return output_path
        
    def _build_filter_complex(self, composition: Dict, resources: Dict) -> str:
        """
        Constrói a string de filtros complexos do FFmpeg
        
        Args:
            composition: Configuração da composição
            resources: Recursos preparados
            
        Returns:
            str: String de filtros complexos
        """
        filters = []
        
        # Processar cada tipo de filtro
        if composition.get('transitions'):
            filters.extend(self._build_transition_filters(composition['transitions']))
            
        if composition.get('overlays'):
            filters.extend(self._build_overlay_filters(composition['overlays']))
            
        if composition.get('text'):
            filters.extend(self._build_text_filters(composition['text']))
            
        return ';'.join(filters) if filters else None
        
    def _build_transition_filters(self, transitions: List[Dict]) -> List[str]:
        """Constrói filtros de transição"""
        filters = []
        for transition in transitions:
            if transition['type'] == 'fade':
                filters.append(
                    f"fade=t=in:st={transition['start']}:d={transition['duration']}"
                )
        return filters
        
    def _build_overlay_filters(self, overlays: List[Dict]) -> List[str]:
        """Constrói filtros de overlay"""
        filters = []
        for overlay in overlays:
            filters.append(
                f"overlay={overlay['x']}:{overlay['y']}"
                f":enable='between(t,{overlay['start']},{overlay['end']})'"
            )
        return filters
        
    def _build_text_filters(self, texts: List[Dict]) -> List[str]:
        """Constrói filtros de texto"""
        filters = []
        for text in texts:
            filters.append(
                f"drawtext=text='{text['content']}'"
                f":x={text['x']}:y={text['y']}"
                f":fontsize={text['size']}"
                f":fontcolor={text['color']}"
            )
        return filters 