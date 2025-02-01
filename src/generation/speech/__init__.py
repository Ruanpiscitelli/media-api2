"""
Módulo de síntese de voz do sistema.
"""

from .pipeline import SpeechPipeline
from .models import FishSpeechModel

__all__ = ['SpeechPipeline', 'FishSpeechModel'] 