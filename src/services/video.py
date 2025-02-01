"""
Serviço para geração e edição de vídeos.
Integra FastHuayuan, FFmpeg e Fish Speech para composição.
"""

import logging
import asyncio
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import torch

from src.core.config import settings
from src.generation.video.fast_huayuan import FastHuayuanGenerator
from src.generation.video.compositor import VideoCompositor
from src.generation.speech.pipeline import SpeechPipeline
from src.core.cache import cache
from src.utils.video import VideoProcessor

logger = logging.getLogger(__name__)

class VideoService:
    """
    Serviço para geração e edição de vídeos.
    Integra diferentes componentes para criar vídeos completos.
    """
    
    def __init__(self):
        """Inicializa o serviço com todos os componentes."""
        self.generator = FastHuayuanGenerator()
        self.compositor = VideoCompositor()
        self.speech_pipeline = SpeechPipeline()
        self.processor = VideoProcessor()
        self.cache = cache
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
    @classmethod
    async def create(cls) -> 'VideoService':
        service = cls()
        await service.initialize()
        return service
        
    async def initialize(self):
        """Inicializa recursos necessários"""
        try:
            # Criar diretórios
            Path(settings.MEDIA_DIR).mkdir(parents=True, exist_ok=True)
            Path(settings.CACHE_DIR).mkdir(parents=True, exist_ok=True)
            logger.info("✅ Diretórios criados")
        except Exception as e:
            logger.error(f"❌ Erro na inicialização: {e}")
            raise
        
    async def validate_project(self, scenes: List[Dict]) -> Dict:
        """
        Valida projeto de vídeo e retorna metadados.
        
        Args:
            scenes: Lista de cenas do vídeo
            
        Returns:
            Dicionário com metadados do projeto
        """
        try:
            total_duration = sum(scene.get('duration', 0) for scene in scenes)
            total_elements = sum(len(scene.get('elements', [])) for scene in scenes)
            
            if total_duration > settings.MAX_VIDEO_DURATION:
                raise ValueError(f"Duração total ({total_duration}s) excede o limite")
                
            return {
                'duration': total_duration,
                'scenes': len(scenes),
                'elements': total_elements
            }
        except Exception as e:
            logger.error(f"Erro validando projeto: {e}")
            raise
            
    async def estimate_resources(self, project: Dict) -> Dict:
        """
        Estima recursos necessários para o projeto.
        
        Args:
            project: Configuração do projeto
            
        Returns:
            Dicionário com estimativas de recursos
        """
        try:
            scenes = project['scenes']
            audio = project.get('audio')
            
            # Estima VRAM por cena
            vram_per_scene = 4096  # 4GB base
            total_vram = len(scenes) * vram_per_scene
            
            # Ajusta baseado em elementos
            for scene in scenes:
                for element in scene['elements']:
                    if element['type'] in ['image', 'video']:
                        total_vram += 1024  # +1GB por mídia
                        
            # Ajusta para áudio
            if audio and audio.get('text'):
                total_vram += 2048  # +2GB para síntese de voz
                
            return {
                'vram_required': total_vram,
                'disk_space': total_vram * 2,  # Estimativa aproximada
                'processing_time': len(scenes) * 60  # 1 min por cena
            }
            
        except Exception as e:
            logger.error(f"Erro estimando recursos: {e}")
            raise
            
    async def process_video(self, project_id: str) -> Dict:
        """Processa um projeto de vídeo"""
        try:
            # Obter projeto do cache
            project = await self.cache.get(f"project:{project_id}")
            if not project:
                raise ValueError(f"Projeto {project_id} não encontrado")
                
            # Processar cenas
            results = []
            for scene in project['scenes']:
                result = await self._process_scene(scene)
                results.append(result)
                
            return {
                'status': 'completed',
                'scenes': len(results),
                'duration': sum(r['duration'] for r in results)
            }
            
        except Exception as e:
            logger.error(f"Erro processando vídeo: {e}")
            raise
            
    async def _process_scene(self, scene: Dict) -> Dict:
        """Processa uma cena individual"""
        try:
            return {
                'duration': scene.get('duration', 0),
                'elements': len(scene.get('elements', []))
            }
        except Exception as e:
            logger.error(f"Erro processando cena: {e}")
            raise
            
    async def _process_audio(self, audio_config: Dict) -> Optional[str]:
        """
        Processa configuração de áudio.
        
        Args:
            audio_config: Configuração do áudio
            
        Returns:
            Caminho do arquivo de áudio processado
        """
        try:
            audio_paths = []
            
            # Gera narração se necessário
            if audio_config.get('text'):
                narration = await self.speech_pipeline.generate_speech({
                    'text': audio_config['text'],
                    'voice_id': audio_config.get('voice_id'),
                    'volume': audio_config.get('volume', {}).get('narration', 1.0)
                })
                audio_paths.append(narration['audio_path'])
                
            # Processa música de fundo
            if audio_config.get('music_url'):
                music = await self.processor.download_audio(
                    url=audio_config['music_url'],
                    volume=audio_config.get('volume', {}).get('music', 0.3)
                )
                audio_paths.append(music)
                
            # Combina áudios se necessário
            if len(audio_paths) > 1:
                return await self.processor.mix_audio(
                    audio_paths,
                    volumes=[
                        audio_config.get('volume', {}).get('narration', 1.0),
                        audio_config.get('volume', {}).get('music', 0.3)
                    ]
                )
            elif audio_paths:
                return audio_paths[0]
                
            return None
            
        except Exception as e:
            logger.error(f"Erro processando áudio: {e}")
            raise
            
    async def _update_progress(self, task_id: str, progress: float):
        """Atualiza progresso da tarefa no cache."""
        try:
            await cache.update_task(task_id, {'progress': progress})
        except Exception as e:
            logger.error(f"Erro atualizando progresso: {e}")
            
    async def get_project_status(self, project_id: str) -> Dict:
        """
        Retorna status atual do projeto.
        
        Args:
            project_id: ID do projeto
            
        Returns:
            Dicionário com status atual
        """
        try:
            task = await cache.get_task(project_id)
            if not task:
                raise ValueError(f"Projeto {project_id} não encontrado")
                
            return {
                'project_id': project_id,
                'status': 'error' if task.get('progress') == -1 else 'processing' if task.get('progress') < 100 else 'completed',
                'progress': task.get('progress', 0),
                'estimated_time': task.get('estimated_time', 0)
            }
            
        except Exception as e:
            logger.error(f"Erro obtendo status: {e}")
            raise
            
    async def generate_preview(
        self,
        project_id: str,
        scene_index: int,
        time: float
    ) -> Dict:
        """
        Gera preview de uma cena.
        
        Args:
            project_id: ID do projeto
            scene_index: Índice da cena
            time: Momento do vídeo em segundos
            
        Returns:
            Dicionário com URL da preview
        """
        try:
            # Recupera projeto
            task = await cache.get_task(project_id)
            if not task:
                raise ValueError(f"Projeto {project_id} não encontrado")
                
            # Valida índice da cena
            scenes = task['params']['scenes']
            if scene_index >= len(scenes):
                raise ValueError(f"Cena {scene_index} não existe")
                
            # Gera frame
            preview = await self.compositor.generate_preview(
                scene=scenes[scene_index],
                time=time
            )
            
            return {
                'preview_url': preview,
                'timestamp': time
            }
            
        except Exception as e:
            logger.error(f"Erro gerando preview: {e}")
            raise

    @staticmethod
    async def validate_ffmpeg_capabilities():
        """Valida recursos do FFmpeg antes de processar"""
        try:
            # Verificar versão mínima
            version = await get_ffmpeg_version()
            if version < "4.0":
                raise RuntimeError(f"FFmpeg versão {version} muito antiga. Mínimo: 4.0")
            
            # Verificar aceleração de hardware
            has_cuda = await check_cuda_support()
            if not has_cuda:
                logger.warning("FFmpeg sem suporte a CUDA - processamento será mais lento")
            
            # Verificar limites do sistema
            import resource
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            if soft < 1024:
                logger.warning(
                    f"Limite de arquivos abertos muito baixo: {soft}. "
                    "Pode causar erros em processamento em lote"
                )
            
        except Exception as e:
            raise RuntimeError(f"Erro validando FFmpeg: {e}") 

# Instância global
video_service = VideoService()

async def get_video_service() -> VideoService:
    """Retorna instância do serviço de vídeo"""
    return video_service 