"""
Sistema de filtros para processamento de vídeo.
Gerencia a criação e aplicação de filtros FFmpeg.
"""

from typing import Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)

class FilterManager:
    def __init__(self):
        """Inicializa o gerenciador de filtros"""
        self.available_filters = {
            'fade': self.create_fade_filter,
            'overlay': self.create_overlay_filter,
            'text': self.create_text_filter,
            'subtitles': self.create_subtitles_filter,
            'scale': self.create_scale_filter,
            'crop': self.create_crop_filter,
            'rotate': self.create_rotate_filter,
            'speed': self.create_speed_filter,
            'volume': self.create_volume_filter,
            'eq': self.create_eq_filter
        }
        
    def create_fade_filter(
        self,
        duration: float,
        type: str = "in",
        start_time: Optional[float] = None
    ) -> str:
        """
        Cria filtro de fade
        
        Args:
            duration: Duração do fade em segundos
            type: Tipo de fade ("in" ou "out")
            start_time: Tempo inicial do fade
            
        Returns:
            str: String do filtro FFmpeg
        """
        filter_str = f"fade=t={type}:d={duration}"
        
        if start_time is not None:
            filter_str += f":st={start_time}"
            
        return filter_str
        
    def create_overlay_filter(
        self,
        x: Union[int, str],
        y: Union[int, str],
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        alpha: Optional[float] = None
    ) -> str:
        """
        Cria filtro de overlay
        
        Args:
            x: Posição X (número ou expressão)
            y: Posição Y (número ou expressão)
            start_time: Tempo inicial do overlay
            end_time: Tempo final do overlay
            alpha: Valor de transparência (0-1)
            
        Returns:
            str: String do filtro FFmpeg
        """
        filter_str = f"overlay={x}:{y}"
        
        if start_time is not None and end_time is not None:
            filter_str += f":enable='between(t,{start_time},{end_time})'"
            
        if alpha is not None:
            filter_str += f":alpha={alpha}"
            
        return filter_str
        
    def create_text_filter(
        self,
        text: str,
        x: Union[int, str],
        y: Union[int, str],
        font: str = "Arial",
        size: int = 24,
        color: str = "white",
        box: bool = False,
        box_color: str = "black@0.5",
        shadow: bool = False
    ) -> str:
        """
        Cria filtro para texto
        
        Args:
            text: Texto a ser exibido
            x: Posição X
            y: Posição Y
            font: Nome da fonte
            size: Tamanho da fonte
            color: Cor do texto
            box: Se deve ter caixa de fundo
            box_color: Cor da caixa de fundo
            shadow: Se deve ter sombra
            
        Returns:
            str: String do filtro FFmpeg
        """
        filter_str = (
            f"drawtext=text='{text}':x={x}:y={y}:"
            f"fontfile={font}:fontsize={size}:fontcolor={color}"
        )
        
        if box:
            filter_str += f":box=1:boxcolor={box_color}"
            
        if shadow:
            filter_str += ":shadowx=2:shadowy=2:shadowcolor=black@0.5"
            
        return filter_str
        
    def create_subtitles_filter(
        self,
        file_path: str,
        style: Optional[Dict] = None
    ) -> str:
        """
        Cria filtro para legendas
        
        Args:
            file_path: Caminho do arquivo de legendas
            style: Dicionário com estilo das legendas
            
        Returns:
            str: String do filtro FFmpeg
        """
        default_style = {
            'FontSize': 24,
            'PrimaryColour': 'white',
            'Alignment': 2,
            'MarginV': 20
        }
        
        subtitle_style = {**default_style, **(style or {})}
        style_str = ','.join(f"{k}={v}" for k, v in subtitle_style.items())
        
        return f"subtitles={file_path}:force_style='{style_str}'"
        
    def create_scale_filter(
        self,
        width: Union[int, str],
        height: Union[int, str],
        maintain_aspect: bool = True,
        scaling_algorithm: str = "lanczos"
    ) -> str:
        """
        Cria filtro de escala
        
        Args:
            width: Largura desejada
            height: Altura desejada
            maintain_aspect: Manter proporção
            scaling_algorithm: Algoritmo de escala
            
        Returns:
            str: String do filtro FFmpeg
        """
        if maintain_aspect:
            return f"scale={width}:{height}:force_original_aspect_ratio=decrease,scale={scaling_algorithm}"
        return f"scale={width}:{height}"
        
    def create_crop_filter(
        self,
        width: int,
        height: int,
        x: int,
        y: int
    ) -> str:
        """
        Cria filtro de corte
        
        Args:
            width: Largura do corte
            height: Altura do corte
            x: Posição X inicial
            y: Posição Y inicial
            
        Returns:
            str: String do filtro FFmpeg
        """
        return f"crop={width}:{height}:{x}:{y}"
        
    def create_rotate_filter(
        self,
        angle: float,
        maintain_size: bool = True
    ) -> str:
        """
        Cria filtro de rotação
        
        Args:
            angle: Ângulo de rotação em graus
            maintain_size: Manter tamanho original
            
        Returns:
            str: String do filtro FFmpeg
        """
        if maintain_size:
            return f"rotate={angle}*PI/180"
        return f"rotate={angle}*PI/180:ow=rotw({angle}*PI/180):oh=roth({angle}*PI/180)"
        
    def create_speed_filter(
        self,
        speed: float,
        maintain_audio_pitch: bool = True
    ) -> str:
        """
        Cria filtro de velocidade
        
        Args:
            speed: Fator de velocidade (1.0 = normal)
            maintain_audio_pitch: Manter tom do áudio
            
        Returns:
            str: String do filtro FFmpeg
        """
        video_filter = f"setpts={1/speed}*PTS"
        
        if maintain_audio_pitch:
            return f"{video_filter},asetrate=44100*{speed},aresample=44100"
        return f"{video_filter},atempo={speed}"
        
    def create_volume_filter(
        self,
        volume: float,
        type: str = "factor"
    ) -> str:
        """
        Cria filtro de volume
        
        Args:
            volume: Valor do volume
            type: Tipo de ajuste ("factor" ou "db")
            
        Returns:
            str: String do filtro FFmpeg
        """
        if type == "db":
            return f"volume={volume}dB"
        return f"volume={volume}"
        
    def create_eq_filter(
        self,
        contrast: float = 1.0,
        brightness: float = 0.0,
        saturation: float = 1.0,
        gamma: float = 1.0
    ) -> str:
        """
        Cria filtro de equalização
        
        Args:
            contrast: Valor do contraste
            brightness: Valor do brilho
            saturation: Valor da saturação
            gamma: Valor do gamma
            
        Returns:
            str: String do filtro FFmpeg
        """
        return (
            f"eq=contrast={contrast}:brightness={brightness}:"
            f"saturation={saturation}:gamma={gamma}"
        )
        
    def combine_filters(self, filters: List[str]) -> str:
        """
        Combina múltiplos filtros
        
        Args:
            filters: Lista de strings de filtros
            
        Returns:
            str: String combinada de filtros
        """
        return ','.join(filter for filter in filters if filter)