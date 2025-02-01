"""
Sistema de composição de vídeo.
Integra todos os componentes para criar vídeos complexos.
"""

import logging
import os
import tempfile
from typing import List, Dict, Optional
import asyncio

from src.core.config import settings
from src.generation.video.compositor import VideoCompositor
from src.generation.video.fast_huayuan import FastHuayuanGenerator
from src.generation.speech.pipeline import SpeechPipeline
from src.utils.video import VideoProcessor

logger = logging.getLogger(__name__)

class VideoCompositionSystem:
    """
    Sistema de composição de vídeo.
    Integra diferentes componentes para criar vídeos complexos.
    """
    
    def __init__(self):
        """Inicializa o sistema com todos os componentes."""
        self.compositor = VideoCompositor()
        self.generator = FastHuayuanGenerator()
        self.speech = SpeechPipeline()
        self.processor = VideoProcessor()
        
    async def create_complex_composition(
        self,
        resources: Dict,
        settings: Dict,
        output_format: str = 'mp4'
    ) -> Dict:
        """
        Cria composição complexa de vídeo.
        
        Args:
            resources: Recursos para composição
            settings: Configurações do vídeo
            output_format: Formato de saída
            
        Returns:
            Dicionário com resultado
        """
        try:
            # Processa recursos em paralelo
            tasks = []
            
            # Processa vídeos
            if 'videos' in resources:
                for video in resources['videos']:
                    tasks.append(
                        self.processor.load_video(
                            path=video['path'],
                            position=video.get('position'),
                            style=video.get('style')
                        )
                    )
                    
            # Processa imagens
            if 'images' in resources:
                for image in resources['images']:
                    tasks.append(
                        self.processor.load_image(
                            path=image['path'],
                            position=image.get('position'),
                            style=image.get('style')
                        )
                    )
                    
            # Processa áudio
            if 'audio' in resources:
                tasks.append(
                    self._process_audio_resources(resources['audio'])
                )
                
            # Aguarda processamento
            results = await asyncio.gather(*tasks)
            
            # Separa resultados
            video_elements = []
            image_elements = []
            audio_path = None
            
            for result in results:
                if isinstance(result, dict):
                    if result['type'] == 'video':
                        video_elements.append(result)
                    elif result['type'] == 'image':
                        image_elements.append(result)
                else:
                    audio_path = result
                    
            # Cria composição final
            with tempfile.TemporaryDirectory() as temp_dir:
                # Combina elementos em cenas
                scenes = []
                
                # Cria cena para cada vídeo
                for video in video_elements:
                    scene = await self.compositor.compose_scene(
                        elements=[video],
                        duration=settings.get('duration', 10.0)
                    )
                    scenes.append(scene)
                    
                # Cria cena para imagens
                if image_elements:
                    scene = await self.compositor.compose_scene(
                        elements=image_elements,
                        duration=settings.get('image_duration', 5.0)
                    )
                    scenes.append(scene)
                    
                # Combina cenas
                output_path = os.path.join(temp_dir, f'output.{output_format}')
                
                final_video = await self.compositor.compose_video(
                    scenes=scenes,
                    audio_path=audio_path,
                    format=output_format,
                    quality=settings.get('quality', 'high')
                )
                
                # Move para diretório final
                final_path = os.path.join(
                    settings.MEDIA_DIR,
                    'videos',
                    os.path.basename(final_video)
                )
                
                os.rename(final_video, final_path)
                
                return {
                    'url': f"/media/videos/{os.path.basename(final_path)}",
                    'duration': sum(scene.get('duration', 0) for scene in scenes),
                    'format': output_format
                }
                
        except Exception as e:
            logger.error(f"Erro na composição: {e}")
            raise
            
    async def create_slideshow(
        self,
        image_paths: List[str],
        duration: float = 5.0,
        transition: str = 'fade',
        audio_path: Optional[str] = None,
        settings: Optional[Dict] = None
    ) -> Dict:
        """
        Cria slideshow a partir de imagens.
        
        Args:
            image_paths: Lista de caminhos de imagens
            duration: Duração por imagem
            transition: Tipo de transição
            audio_path: Caminho do áudio
            settings: Configurações adicionais
            
        Returns:
            Dicionário com resultado
        """
        try:
            # Carrega imagens
            elements = []
            for path in image_paths:
                result = await self.processor.load_image(
                    path=path,
                    style=settings.get('image_style')
                )
                elements.append(result)
                
            # Cria cenas
            scenes = []
            for element in elements:
                scene = await self.compositor.compose_scene(
                    elements=[element],
                    duration=duration,
                    transition={'type': transition, 'duration': 0.5}
                )
                scenes.append(scene)
                
            # Combina cenas
            final_video = await self.compositor.compose_video(
                scenes=scenes,
                audio_path=audio_path,
                quality=settings.get('quality', 'high')
            )
            
            # Move para diretório final
            final_path = os.path.join(
                settings.MEDIA_DIR,
                'videos',
                f'slideshow_{len(scenes)}.mp4'
            )
            
            os.rename(final_video, final_path)
            
            return {
                'url': f"/media/videos/slideshow_{len(scenes)}.mp4",
                'duration': len(scenes) * duration,
                'format': 'mp4'
            }
            
        except Exception as e:
            logger.error(f"Erro criando slideshow: {e}")
            raise
            
    async def create_video_with_overlay(
        self,
        base_video: str,
        overlay_video: str,
        position: Dict[str, float],
        timing: Dict[str, float],
        output_path: str
    ) -> Dict:
        """
        Cria vídeo com overlay.
        
        Args:
            base_video: Vídeo base
            overlay_video: Vídeo de overlay
            position: Posição do overlay
            timing: Tempos de início/fim
            output_path: Caminho de saída
            
        Returns:
            Dicionário com resultado
        """
        try:
            # Carrega vídeos
            base = await self.processor.load_video(base_video)
            overlay = await self.processor.load_video(
                overlay_video,
                position=position
            )
            
            # Cria cena
            scene = await self.compositor.compose_scene(
                elements=[base, overlay],
                duration=timing['end'] - timing['start']
            )
            
            # Salva resultado
            final_video = await self.compositor.compose_video(
                scenes=[scene],
                format='mp4',
                quality='high'
            )
            
            os.rename(final_video, output_path)
            
            return {
                'url': f"/media/videos/{os.path.basename(output_path)}",
                'duration': timing['end'] - timing['start'],
                'format': 'mp4'
            }
            
        except Exception as e:
            logger.error(f"Erro criando vídeo com overlay: {e}")
            raise
            
    async def _process_audio_resources(self, audio_config: Dict) -> Optional[str]:
        """
        Processa recursos de áudio.
        
        Args:
            audio_config: Configuração do áudio
            
        Returns:
            Caminho do áudio processado
        """
        try:
            audio_paths = []
            
            # Processa narração
            if 'text' in audio_config:
                result = await self.speech.generate_speech(
                    text=audio_config['text'],
                    voice_id=audio_config.get('voice_id')
                )
                audio_paths.append(result['audio_path'])
                
            # Processa música
            if 'music' in audio_config:
                path = await self.processor.download_audio(
                    url=audio_config['music'],
                    volume=audio_config.get('music_volume', 0.3)
                )
                audio_paths.append(path)
                
            # Combina áudios
            if len(audio_paths) > 1:
                return await self.processor.mix_audio(
                    audio_paths=audio_paths,
                    volumes=[1.0, 0.3]  # Narração mais alta que música
                )
            elif audio_paths:
                return audio_paths[0]
                
            return None
            
        except Exception as e:
            logger.error(f"Erro processando áudio: {e}")
            raise 