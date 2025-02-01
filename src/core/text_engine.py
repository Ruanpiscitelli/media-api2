"""
Motor de processamento de texto com suporte a múltiplos idiomas e fontes.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

logger = logging.getLogger(__name__)

class TextEngine:
    """
    Motor de processamento de texto com suporte a múltiplos idiomas.
    """
    
    def __init__(self):
        """Inicializa o motor de texto."""
        self.fonts_dir = "assets/fonts"
        self._load_fonts()
        
    def _load_fonts(self):
        """Carrega fontes disponíveis."""
        self.fonts = {}
        os.makedirs(self.fonts_dir, exist_ok=True)
        
        # Adicionar fonte padrão
        self.default_font = "Arial"
        
    async def render_text(
        self,
        text: str,
        font_name: str = None,
        size: int = 32,
        color: Union[str, Tuple[int, int, int]] = "white",
        max_width: Optional[int] = None,
        language: str = "pt-BR",
        alignment: str = "left"
    ) -> Image.Image:
        """
        Renderiza texto em uma imagem.
        
        Args:
            text: Texto para renderizar
            font_name: Nome da fonte
            size: Tamanho da fonte
            color: Cor do texto
            max_width: Largura máxima
            language: Código do idioma
            alignment: Alinhamento do texto
            
        Returns:
            Imagem PIL com o texto renderizado
        """
        try:
            # Usar fonte padrão se não especificada
            font_name = font_name or self.default_font
            
            # Criar fonte
            try:
                font = ImageFont.truetype(font_name, size)
            except:
                font = ImageFont.load_default()
                
            # Calcular tamanho do texto
            bbox = font.getbbox(text)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            
            if max_width and width > max_width:
                # TODO: Implementar quebra de linha
                width = max_width
                
            # Criar imagem
            image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # Desenhar texto
            draw.text(
                (0, 0),
                text,
                font=font,
                fill=color,
                align=alignment
            )
            
            return image
            
        except Exception as e:
            logger.error(f"Erro renderizando texto: {e}")
            raise
            
    async def get_text_size(
        self,
        text: str,
        font_name: str = None,
        size: int = 32
    ) -> Tuple[int, int]:
        """
        Retorna o tamanho que o texto ocupará.
        
        Args:
            text: Texto para medir
            font_name: Nome da fonte
            size: Tamanho da fonte
            
        Returns:
            Tupla (largura, altura)
        """
        try:
            # Usar fonte padrão se não especificada
            font_name = font_name or self.default_font
            
            # Criar fonte
            try:
                font = ImageFont.truetype(font_name, size)
            except:
                font = ImageFont.load_default()
                
            # Calcular tamanho
            bbox = font.getbbox(text)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            
            return width, height
            
        except Exception as e:
            logger.error(f"Erro medindo texto: {e}")
            raise

# Instância global do motor de texto
text_engine = TextEngine() 