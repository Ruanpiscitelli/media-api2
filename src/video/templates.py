"""
Sistema de templates para composições de vídeo.
Define templates pré-configurados para diferentes tipos de vídeo.
"""

from typing import Dict, Any

# Templates para diferentes tipos de vídeo
VIDEO_TEMPLATES = {
    'presentation': {
        'format': 'mp4',
        'resolution': '1920x1080',
        'slide_duration': 5.0,
        'transition': {
            'type': 'fade',
            'duration': 1.0
        },
        'text_style': {
            'font': 'Arial',
            'size': 48,
            'color': 'white',
            'position': 'bottom',
            'box': True,
            'box_color': 'black@0.5'
        },
        'audio': {
            'normalize': True,
            'volume': 1.0
        }
    },
    'social_media': {
        'format': 'mp4',
        'resolution': '1080x1080',
        'slide_duration': 3.0,
        'transition': {
            'type': 'dissolve',
            'duration': 0.5
        },
        'text_style': {
            'font': 'Roboto',
            'size': 36,
            'color': 'white',
            'position': 'center',
            'shadow': True
        },
        'audio': {
            'normalize': True,
            'volume': 1.2
        }
    },
    'story': {
        'format': 'mp4',
        'resolution': '1080x1920',
        'slide_duration': 2.0,
        'transition': {
            'type': 'slide',
            'duration': 0.3
        },
        'text_style': {
            'font': 'Helvetica',
            'size': 42,
            'color': 'white',
            'position': 'bottom',
            'box': True,
            'box_color': 'gradient@0.5'
        },
        'audio': {
            'normalize': True,
            'volume': 1.0,
            'fade': {
                'in': 0.5,
                'out': 0.5
            }
        }
    },
    'product': {
        'format': 'mp4',
        'resolution': '1920x1080',
        'slide_duration': 4.0,
        'transition': {
            'type': 'zoom',
            'duration': 0.8
        },
        'text_style': {
            'font': 'Montserrat',
            'size': 40,
            'color': 'white',
            'position': 'bottom_right',
            'shadow': True
        },
        'audio': {
            'normalize': True,
            'volume': 1.1,
            'background_music': {
                'volume': 0.3,
                'fade': True
            }
        }
    },
    'tutorial': {
        'format': 'mp4',
        'resolution': '1920x1080',
        'slide_duration': 6.0,
        'transition': {
            'type': 'fade',
            'duration': 0.5
        },
        'text_style': {
            'font': 'Open Sans',
            'size': 44,
            'color': 'white',
            'position': 'top',
            'box': True,
            'box_color': 'blue@0.3'
        },
        'audio': {
            'normalize': True,
            'volume': 1.2,
            'voice': {
                'enhance': True,
                'noise_reduction': True
            }
        },
        'overlay': {
            'logo': {
                'position': 'top_right',
                'size': '120x120',
                'opacity': 0.8
            }
        }
    }
}

class TemplateManager:
    def __init__(self):
        """Inicializa o gerenciador de templates"""
        self.templates = VIDEO_TEMPLATES
        
    def get_template(self, template_name: str) -> Dict[str, Any]:
        """
        Retorna um template específico
        
        Args:
            template_name: Nome do template
            
        Returns:
            Dict: Configuração do template
            
        Raises:
            ValueError: Se o template não existir
        """
        if template_name not in self.templates:
            raise ValueError(f"Template não encontrado: {template_name}")
            
        return self.templates[template_name].copy()
        
    def customize_template(
        self,
        template_name: str,
        customizations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Personaliza um template existente
        
        Args:
            template_name: Nome do template base
            customizations: Dicionário com personalizações
            
        Returns:
            Dict: Template personalizado
            
        Raises:
            ValueError: Se o template não existir
        """
        template = self.get_template(template_name)
        
        # Aplicar personalizações recursivamente
        self._deep_update(template, customizations)
        
        return template
        
    def _deep_update(self, base: Dict, update: Dict) -> None:
        """
        Atualiza um dicionário recursivamente
        
        Args:
            base: Dicionário base
            update: Dicionário com atualizações
        """
        for key, value in update.items():
            if isinstance(value, dict) and key in base:
                self._deep_update(base[key], value)
            else:
                base[key] = value
                
    def create_template(
        self,
        name: str,
        config: Dict[str, Any]
    ) -> None:
        """
        Cria um novo template
        
        Args:
            name: Nome do novo template
            config: Configuração do template
            
        Raises:
            ValueError: Se o template já existir
        """
        if name in self.templates:
            raise ValueError(f"Template já existe: {name}")
            
        self.templates[name] = config
        
    def get_template_names(self) -> list:
        """
        Retorna lista de nomes de templates disponíveis
        
        Returns:
            list: Lista de nomes de templates
        """
        return list(self.templates.keys())
        
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """
        Retorna informações sobre um template
        
        Args:
            template_name: Nome do template
            
        Returns:
            Dict: Informações do template
            
        Raises:
            ValueError: Se o template não existir
        """
        template = self.get_template(template_name)
        
        return {
            'name': template_name,
            'format': template['format'],
            'resolution': template['resolution'],
            'duration': template['slide_duration'],
            'features': [
                'transitions' if 'transition' in template else None,
                'text' if 'text_style' in template else None,
                'audio' if 'audio' in template else None,
                'overlay' if 'overlay' in template else None
            ]
        } 