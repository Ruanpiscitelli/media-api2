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

from src.core.config import settings
from src.generation.video.fast_huayuan import FastHuayuanGenerator
from src.generation.video.compositor import VideoCompositor
from src.generation.speech.pipeline import SpeechPipeline
from src.core.cache.manager import cache_manager
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
        
    async def validate_project(self, scenes: List[Dict]) -> Dict:
        """
        Valida projeto de vídeo e retorna metadados.
        
        Args:
            scenes: Lista de cenas do vídeo
            
        Returns:
            Dicionário com metadados do projeto
        """
        try:
            total_duration = sum(scene['duration'] for scene in scenes)
            total_elements = sum(len(scene['elements']) for scene in scenes)
            
            # Validações básicas
            if total_duration > settings.MAX_VIDEO_DURATION:
                raise ValueError(
                    f"Duração total ({total_duration}s) excede o limite "
                    f"({settings.MAX_VIDEO_DURATION}s)"
                )
                
            if total_elements > settings.MAX_VIDEO_ELEMENTS:
                raise ValueError(
                    f"Número de elementos ({total_elements}) excede o limite "
                    f"({settings.MAX_VIDEO_ELEMENTS})"
                )
                
            return {
                'duration': total_duration,
                'scenes': len(scenes),
                'elements': total_elements,
                'validated_at': datetime.utcnow().isoformat()
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
            
    async def process_video_project(
        self,
        task_id: str,
        gpu_id: str
    ) -> Dict:
        """
        Processa projeto de vídeo completo.
        
        Args:
            task_id: ID da tarefa
            gpu_id: ID da GPU para processamento
            
        Returns:
            Dicionário com resultado do processamento
        """
        try:
            # Recupera configuração da tarefa
            task = await cache_manager.get_task(task_id)
            project = task['params']
            
            # Processa cenas
            scene_results = []
            for i, scene in enumerate(project['scenes']):
                # Atualiza progresso
                await self._update_progress(task_id, (i / len(project['scenes'])) * 100)
                
                # Processa cena
                result = await self._process_scene(scene, gpu_id)
                scene_results.append(result)
                
            # Processa áudio se necessário
            audio_path = None
            if project.get('audio'):
                audio_path = await self._process_audio(project['audio'])
                
            # Combina cenas e áudio
            final_video = await self.compositor.compose_video(
                scenes=scene_results,
                audio_path=audio_path,
                format=project.get('format', 'mp4'),
                quality=project.get('quality', 'high')
            )
            
            # Atualiza status
            await self._update_progress(task_id, 100)
            
            return {
                'status': 'completed',
                'video_path': final_video,
                'metadata': {
                    'duration': sum(scene['duration'] for scene in project['scenes']),
                    'format': project.get('format', 'mp4'),
                    'quality': project.get('quality', 'high'),
                    'scenes': len(project['scenes']),
                    'has_audio': audio_path is not None
                }
            }
            
        except Exception as e:
            logger.error(f"Erro processando projeto: {e}")
            await self._update_progress(task_id, -1)  # Indica erro
            raise
            
    async def _process_scene(self, scene: Dict, gpu_id: str) -> Dict:
        """
        Processa uma cena individual.
        
        Args:
            scene: Configuração da cena
            gpu_id: ID da GPU
            
        Returns:
            Dicionário com resultado do processamento
        """
        try:
            # Processa elementos
            processed_elements = []
            for element in scene['elements']:
                if element['type'] == 'text':
                    # Renderiza texto
                    result = await self.compositor.render_text(
                        text=element['content'],
                        style=element.get('style', {}),
                        position=element.get('position', {'x': 0.5, 'y': 0.5})
                    )
                elif element['type'] == 'image':
                    # Carrega/processa imagem
                    result = await self.processor.load_image(
                        path=element['content'],
                        position=element.get('position'),
                        style=element.get('style')
                    )
                elif element['type'] == 'video':
                    # Carrega/processa vídeo
                    result = await self.processor.load_video(
                        path=element['content'],
                        position=element.get('position'),
                        style=element.get('style')
                    )
                    
                processed_elements.append(result)
                
            # Combina elementos
            scene_video = await self.compositor.compose_scene(
                elements=processed_elements,
                duration=scene['duration'],
                transition=scene.get('transition')
            )
            
            return {
                'video_path': scene_video,
                'duration': scene['duration'],
                'elements': len(processed_elements)
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
            await cache_manager.update_task(task_id, {'progress': progress})
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
            task = await cache_manager.get_task(project_id)
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
            task = await cache_manager.get_task(project_id)
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