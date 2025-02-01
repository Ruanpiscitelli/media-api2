"""
Compositor de vídeo para combinar elementos e cenas.
Implementa renderização de texto, imagens e transições.
"""

import logging
import os
import tempfile
from typing import List, Dict, Optional
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import ffmpeg

from src.core.config import settings
from src.utils.video import VideoProcessor

logger = logging.getLogger(__name__)

class VideoCompositor:
    """
    Compositor de vídeo para combinar elementos e cenas.
    Implementa efeitos e transições.
    """
    
    def __init__(self):
        """Inicializa o compositor."""
        self.processor = VideoProcessor()
        self.font_path = os.path.join(
            settings.ASSETS_DIR,
            'fonts/OpenSans-Regular.ttf'
        )
        
    async def compose_video(
        self,
        scenes: List[Dict],
        audio_path: Optional[str] = None,
        format: str = 'mp4',
        quality: str = 'high'
    ) -> str:
        """
        Combina cenas em vídeo final.
        
        Args:
            scenes: Lista de cenas processadas
            audio_path: Caminho do áudio
            format: Formato do vídeo
            quality: Qualidade do vídeo
            
        Returns:
            Caminho do vídeo final
        """
        try:
            # Cria diretório temporário
            with tempfile.TemporaryDirectory() as temp_dir:
                # Combina cenas
                video_path = os.path.join(temp_dir, f'output.{format}')
                
                # Lista de inputs para ffmpeg
                inputs = []
                
                # Processa cada cena
                for i, scene in enumerate(scenes):
                    scene_path = scene['video_path']
                    
                    # Aplica transição se não for última cena
                    if i < len(scenes) - 1:
                        next_scene = scenes[i + 1]
                        transition = next_scene.get('transition', {
                            'type': 'fade',
                            'duration': 0.5
                        })
                        
                        # Aplica transição
                        scene_path = await self._apply_transition(
                            scene_path,
                            next_scene['video_path'],
                            transition,
                            temp_dir
                        )
                        
                    inputs.append(scene_path)
                    
                # Concatena vídeos
                stream = ffmpeg.input(
                    'concat:' + '|'.join(inputs),
                    format='mp4'
                )
                
                # Adiciona áudio se fornecido
                if audio_path:
                    audio = ffmpeg.input(audio_path)
                    stream = ffmpeg.output(
                        stream,
                        audio,
                        video_path,
                        acodec='aac',
                        vcodec='h264',
                        **self._get_quality_settings(quality)
                    )
                else:
                    stream = ffmpeg.output(
                        stream,
                        video_path,
                        vcodec='h264',
                        **self._get_quality_settings(quality)
                    )
                    
                # Executa ffmpeg
                stream.overwrite_output().run(capture_stdout=True, capture_stderr=True)
                
                return video_path
                
        except Exception as e:
            logger.error(f"Erro compondo vídeo: {e}")
            raise
            
    async def compose_scene(
        self,
        elements: List[Dict],
        duration: float,
        transition: Optional[Dict] = None
    ) -> str:
        """
        Combina elementos em uma cena.
        
        Args:
            elements: Lista de elementos processados
            duration: Duração da cena
            transition: Configuração de transição
            
        Returns:
            Caminho do vídeo da cena
        """
        try:
            # Cria diretório temporário
            with tempfile.TemporaryDirectory() as temp_dir:
                # Cria vídeo base
                base_path = os.path.join(temp_dir, 'base.mp4')
                
                # Dimensões do vídeo
                width = settings.VIDEO_WIDTH
                height = settings.VIDEO_HEIGHT
                
                # Cria frames base
                frames = []
                fps = settings.VIDEO_FPS
                total_frames = int(duration * fps)
                
                for _ in range(total_frames):
                    # Cria frame base
                    frame = np.zeros((height, width, 3), dtype=np.uint8)
                    
                    # Adiciona elementos
                    for element in elements:
                        frame = self._add_element_to_frame(
                            frame,
                            element
                        )
                        
                    frames.append(frame)
                    
                # Salva frames como vídeo
                self.processor.save_video(
                    frames,
                    base_path,
                    fps=fps
                )
                
                return base_path
                
        except Exception as e:
            logger.error(f"Erro compondo cena: {e}")
            raise
            
    async def render_text(
        self,
        text: str,
        style: Dict,
        position: Dict[str, float]
    ) -> Dict:
        """
        Renderiza texto como imagem.
        
        Args:
            text: Texto para renderizar
            style: Estilos do texto
            position: Posição do texto
            
        Returns:
            Dicionário com imagem renderizada
        """
        try:
            # Carrega fonte
            font_size = style.get('fontSize', 32)
            font = ImageFont.truetype(self.font_path, font_size)
            
            # Cria imagem base
            img = Image.new(
                'RGBA',
                (settings.VIDEO_WIDTH, settings.VIDEO_HEIGHT),
                (0, 0, 0, 0)
            )
            draw = ImageDraw.Draw(img)
            
            # Calcula posição do texto
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            x = int(position['x'] * settings.VIDEO_WIDTH - text_width / 2)
            y = int(position['y'] * settings.VIDEO_HEIGHT - text_height / 2)
            
            # Renderiza texto
            draw.text(
                (x, y),
                text,
                font=font,
                fill=style.get('color', '#FFFFFF')
            )
            
            return {
                'type': 'text',
                'image': img,
                'position': position,
                'bbox': text_bbox
            }
            
        except Exception as e:
            logger.error(f"Erro renderizando texto: {e}")
            raise
            
    async def generate_preview(
        self,
        scene: Dict,
        time: float
    ) -> str:
        """
        Gera preview de uma cena.
        
        Args:
            scene: Configuração da cena
            time: Momento do vídeo
            
        Returns:
            URL da preview
        """
        try:
            # Processa elementos
            elements = []
            for element in scene['elements']:
                if element['type'] == 'text':
                    result = await self.render_text(
                        text=element['content'],
                        style=element.get('style', {}),
                        position=element.get('position', {'x': 0.5, 'y': 0.5})
                    )
                elif element['type'] == 'image':
                    result = await self.processor.load_image(
                        path=element['content'],
                        position=element.get('position'),
                        style=element.get('style')
                    )
                elif element['type'] == 'video':
                    result = await self.processor.extract_frame(
                        path=element['content'],
                        time=time,
                        position=element.get('position'),
                        style=element.get('style')
                    )
                    
                elements.append(result)
                
            # Cria frame
            frame = np.zeros(
                (settings.VIDEO_HEIGHT, settings.VIDEO_WIDTH, 3),
                dtype=np.uint8
            )
            
            # Adiciona elementos
            for element in elements:
                frame = self._add_element_to_frame(frame, element)
                
            # Salva preview
            preview_path = os.path.join(
                settings.MEDIA_DIR,
                'previews',
                f'preview_{time}.jpg'
            )
            
            cv2.imwrite(preview_path, frame)
            
            return f"/media/previews/preview_{time}.jpg"
            
        except Exception as e:
            logger.error(f"Erro gerando preview: {e}")
            raise
            
    def _add_element_to_frame(
        self,
        frame: np.ndarray,
        element: Dict
    ) -> np.ndarray:
        """
        Adiciona elemento a um frame.
        
        Args:
            frame: Frame base
            element: Elemento para adicionar
            
        Returns:
            Frame com elemento adicionado
        """
        try:
            if element['type'] == 'text':
                # Converte imagem PIL para numpy
                element_img = np.array(element['image'])
                
                # Adiciona texto com alpha blending
                alpha = element_img[:, :, 3] / 255.0
                for c in range(3):
                    frame[:, :, c] = (
                        frame[:, :, c] * (1 - alpha) +
                        element_img[:, :, c] * alpha
                    )
                    
            elif element['type'] in ['image', 'video']:
                # Redimensiona se necessário
                if 'style' in element and 'size' in element['style']:
                    width = int(element['style']['size']['width'])
                    height = int(element['style']['size']['height'])
                    element_img = cv2.resize(
                        element['image'],
                        (width, height)
                    )
                else:
                    element_img = element['image']
                    
                # Calcula posição
                x = int(element['position']['x'] * frame.shape[1])
                y = int(element['position']['y'] * frame.shape[0])
                
                # Adiciona imagem
                frame[y:y+element_img.shape[0], x:x+element_img.shape[1]] = element_img
                
            return frame
            
        except Exception as e:
            logger.error(f"Erro adicionando elemento: {e}")
            return frame
            
    async def _apply_transition(
        self,
        video1_path: str,
        video2_path: str,
        transition: Dict,
        temp_dir: str
    ) -> str:
        """
        Aplica transição entre vídeos.
        
        Args:
            video1_path: Primeiro vídeo
            video2_path: Segundo vídeo
            transition: Configuração da transição
            temp_dir: Diretório temporário
            
        Returns:
            Caminho do vídeo com transição
        """
        try:
            # Configura transição
            transition_type = transition.get('type', 'fade')
            duration = transition.get('duration', 0.5)
            
            # Caminho do output
            output_path = os.path.join(temp_dir, 'transition.mp4')
            
            if transition_type == 'fade':
                # Aplica fade out/in
                stream1 = ffmpeg.input(video1_path)
                stream2 = ffmpeg.input(video2_path)
                
                # Adiciona fade out no primeiro vídeo
                stream1 = ffmpeg.filter(
                    stream1,
                    'fade',
                    type='out',
                    duration=duration
                )
                
                # Adiciona fade in no segundo vídeo
                stream2 = ffmpeg.filter(
                    stream2,
                    'fade',
                    type='in',
                    duration=duration
                )
                
                # Concatena streams
                stream = ffmpeg.concat(
                    stream1,
                    stream2,
                    v=1,
                    a=0
                )
                
            else:
                # Outros tipos de transição
                logger.warning(f"Tipo de transição não suportado: {transition_type}")
                return video1_path
                
            # Salva vídeo
            stream = ffmpeg.output(
                stream,
                output_path,
                vcodec='h264'
            )
            
            stream.overwrite_output().run(
                capture_stdout=True,
                capture_stderr=True
            )
            
            return output_path
            
        except Exception as e:
            logger.error(f"Erro aplicando transição: {e}")
            return video1_path
            
    def _get_quality_settings(self, quality: str) -> Dict:
        """Retorna configurações de qualidade do vídeo."""
        if quality == 'high':
            return {
                'crf': 18,
                'preset': 'slow'
            }
        elif quality == 'medium':
            return {
                'crf': 23,
                'preset': 'medium'
            }
        else:
            return {
                'crf': 28,
                'preset': 'fast'
            } 