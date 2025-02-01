"""
Pipeline completo de síntese de voz.
Integra processamento de texto, geração de voz e processamento de áudio.
"""

import logging
import os
import uuid
from typing import Dict, Optional
import torch
import torchaudio
from prometheus_client import Summary, Histogram

from src.core.config import settings
from .text_processor import TextProcessor
from .voice_generator import VoiceGenerator
from .audio_processor import AudioProcessor

logger = logging.getLogger(__name__)

# Métricas Prometheus
GENERATION_TIME = Summary(
    'speech_generation_seconds',
    'Time spent generating speech'
)

TEXT_LENGTH = Histogram(
    'text_length_chars',
    'Distribution of input text lengths',
    buckets=(10, 50, 100, 200, 500, 1000, 2000, 5000)
)

AUDIO_LENGTH = Histogram(
    'audio_length_seconds',
    'Distribution of generated audio lengths',
    buckets=(1, 5, 10, 30, 60, 120, 300)
)

class SpeechPipeline:
    """
    Pipeline completo para síntese de voz.
    Integra todos os componentes do sistema.
    """
    
    def __init__(self):
        """Inicializa o pipeline com todos os componentes."""
        self.text_processor = TextProcessor()
        self.voice_generator = VoiceGenerator(
            model_path=settings.FISH_SPEECH_MODEL_PATH
        )
        self.audio_processor = AudioProcessor()
        
    @GENERATION_TIME.time()
    async def generate_speech(self, request: Dict) -> Dict:
        """
        Pipeline completo de síntese de voz.
        
        Args:
            request: Dicionário com parâmetros da requisição
            
        Returns:
            Dicionário com resultado e metadados
        """
        try:
            # Registra métricas do texto
            TEXT_LENGTH.observe(len(request['text']))
            
            # Processa texto
            processed_text = self.text_processor.process_text(
                request['text'],
                request.get('language')
            )
            
            # Gera áudio base
            raw_audio = self.voice_generator.generate_speech(
                processed_text,
                voice_id=request['voice_id'],
                emotion=request.get('emotion', 'neutral'),
                speed=request.get('speed', 1.0),
                pitch=request.get('pitch', 0.0),
                volume=request.get('volume', 1.0)
            )
            
            # Processa áudio
            processed_audio = self.audio_processor.process_audio(
                raw_audio,
                sample_rate=request.get('sample_rate', 44100),
                effects=request.get('audio_effects')
            )
            
            # Registra duração do áudio
            duration = len(processed_audio) / request.get('sample_rate', 44100)
            AUDIO_LENGTH.observe(duration)
            
            # Salva resultado
            output_path = await self._save_audio(
                processed_audio,
                request.get('audio_format', 'wav')
            )
            
            return {
                'status': 'success',
                'audio_path': output_path,
                'metadata': {
                    'duration': duration,
                    'text_info': {
                        'original': request['text'],
                        'normalized': processed_text['normalized_text'],
                        'language': processed_text['language']
                    },
                    'voice_info': {
                        'id': request['voice_id'],
                        'emotion': request.get('emotion', 'neutral'),
                        'speed': request.get('speed', 1.0),
                        'pitch': request.get('pitch', 0.0)
                    },
                    'audio_info': {
                        'sample_rate': request.get('sample_rate', 44100),
                        'format': request.get('audio_format', 'wav'),
                        'effects_applied': request.get('audio_effects', {})
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Erro no pipeline: {e}")
            raise
            
    async def _save_audio(
        self,
        audio: torch.Tensor,
        format: str = "wav"
    ) -> str:
        """
        Salva o áudio processado em arquivo.
        
        Args:
            audio: Tensor com áudio
            format: Formato do arquivo
            
        Returns:
            Caminho do arquivo salvo
        """
        try:
            # Cria diretório se não existir
            os.makedirs("outputs/speech", exist_ok=True)
            
            # Gera nome único
            filename = f"speech_{uuid.uuid4()}.{format}"
            output_path = os.path.join("outputs/speech", filename)
            
            # Salva arquivo
            torchaudio.save(
                output_path,
                audio.unsqueeze(0),
                sample_rate=44100,
                format=format
            )
            
            return output_path
            
        except Exception as e:
            logger.error(f"Erro salvando áudio: {e}")
            raise
            
    async def get_available_voices(self) -> Dict:
        """
        Retorna informações sobre vozes disponíveis.
        
        Returns:
            Dicionário com informações das vozes
        """
        try:
            voices = {}
            voice_dir = os.path.join(settings.FISH_SPEECH_MODEL_PATH, "voices")
            
            for file in os.listdir(voice_dir):
                if file.endswith(".json"):
                    voice_id = file.replace(".json", "")
                    with open(os.path.join(voice_dir, file)) as f:
                        voices[voice_id] = json.load(f)
                        
            return {
                'total_voices': len(voices),
                'voices': voices
            }
            
        except Exception as e:
            logger.error(f"Erro listando vozes: {e}")
            return {
                'total_voices': 0,
                'voices': {}
            }
            
    async def get_supported_effects(self) -> Dict:
        """
        Retorna informações sobre efeitos suportados.
        
        Returns:
            Dicionário com informações dos efeitos
        """
        return {
            'reverb': {
                'description': 'Adiciona reverberação ao áudio',
                'parameters': {
                    'room_size': {'type': 'float', 'range': [0.0, 1.0]},
                    'damping': {'type': 'float', 'range': [0.0, 1.0]},
                    'wet_level': {'type': 'float', 'range': [0.0, 1.0]},
                    'dry_level': {'type': 'float', 'range': [0.0, 1.0]}
                }
            },
            'eq': {
                'description': 'Equalização de 3 bandas',
                'parameters': {
                    'low_gain': {'type': 'float', 'range': [0.0, 2.0]},
                    'mid_gain': {'type': 'float', 'range': [0.0, 2.0]},
                    'high_gain': {'type': 'float', 'range': [0.0, 2.0]}
                }
            },
            'compression': {
                'description': 'Compressão dinâmica',
                'parameters': {
                    'threshold': {'type': 'float', 'range': [-60.0, 0.0]},
                    'ratio': {'type': 'float', 'range': [1.0, 20.0]},
                    'attack': {'type': 'float', 'range': [0.001, 0.1]},
                    'release': {'type': 'float', 'range': [0.01, 1.0]}
                }
            }
        }