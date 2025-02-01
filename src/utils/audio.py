"""
Utilitários para processamento de áudio.
"""

import io
import logging
import numpy as np
import soundfile as sf
import librosa
from typing import List, Optional
import torch
import torchaudio
from pydub import AudioSegment
import uuid

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Processador de áudio com funções avançadas."""
    
    def __init__(self):
        """Inicializa o processador."""
        pass
        
    async def concatenate(
        self,
        audio_paths: List[str],
        crossfade: float = 0.3,
        format: str = "wav"
    ) -> str:
        """
        Concatena múltiplos arquivos de áudio com crossfade.
        
        Args:
            audio_paths: Lista de caminhos dos arquivos
            crossfade: Duração do crossfade em segundos
            format: Formato do arquivo de saída
            
        Returns:
            Caminho do arquivo concatenado
        """
        try:
            # Carrega segmentos
            segments = [AudioSegment.from_file(path) for path in audio_paths]
            
            # Configura crossfade
            crossfade_ms = int(crossfade * 1000)
            
            # Concatena com crossfade
            final_audio = segments[0]
            for segment in segments[1:]:
                final_audio = final_audio.append(
                    segment,
                    crossfade=crossfade_ms
                )
                
            # Normaliza volume
            final_audio = final_audio.normalize()
            
            # Gera nome único
            output_path = f"outputs/speech/concat_{uuid.uuid4()}.{format}"
            
            # Exporta
            final_audio.export(
                output_path,
                format=format,
                parameters=["-ac", "1"]  # Mono
            )
            
            return output_path
            
        except Exception as e:
            logger.error(f"Erro concatenando áudios: {e}")
            raise
            
    async def prepare_for_streaming(
        self,
        audio_path: str,
        chunk_size: int = 4096,
        format: str = "wav"
    ) -> bytes:
        """
        Prepara áudio para streaming.
        
        Args:
            audio_path: Caminho do arquivo
            chunk_size: Tamanho do chunk em bytes
            format: Formato do áudio
            
        Returns:
            Chunk de áudio em bytes
        """
        try:
            # Carrega áudio
            audio, sr = librosa.load(audio_path, sr=None)
            
            # Converte para int16
            audio = (audio * 32767).astype(np.int16)
            
            # Cria buffer
            buffer = io.BytesIO()
            
            # Salva no formato correto
            sf.write(
                buffer,
                audio,
                sr,
                format=format,
                subtype='PCM_16'
            )
            
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Erro preparando áudio para streaming: {e}")
            raise
            
    async def apply_effects(
        self,
        audio_path: str,
        effects: Optional[dict] = None
    ) -> str:
        """
        Aplica efeitos no áudio.
        
        Args:
            audio_path: Caminho do arquivo
            effects: Dicionário com efeitos a aplicar
            
        Returns:
            Caminho do arquivo processado
        """
        try:
            if not effects:
                return audio_path
                
            # Carrega áudio
            audio = AudioSegment.from_file(audio_path)
            
            # Aplica efeitos
            if effects.get('normalize'):
                audio = audio.normalize()
                
            if effects.get('remove_silence'):
                audio = self._remove_silence(audio)
                
            if effects.get('reverb'):
                audio = self._apply_reverb(
                    audio,
                    **effects['reverb']
                )
                
            if effects.get('eq'):
                audio = self._apply_eq(
                    audio,
                    **effects['eq']
                )
                
            # Salva resultado
            output_path = f"outputs/speech/processed_{uuid.uuid4()}.wav"
            audio.export(output_path, format="wav")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Erro aplicando efeitos: {e}")
            raise
            
    def _remove_silence(
        self,
        audio: AudioSegment,
        min_silence_len: int = 500,
        silence_thresh: int = -40
    ) -> AudioSegment:
        """Remove silêncios do áudio."""
        chunks = split_on_silence(
            audio,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh
        )
        return sum(chunks, AudioSegment.empty())
        
    def _apply_reverb(
        self,
        audio: AudioSegment,
        room_size: float = 0.5,
        damping: float = 0.5,
        wet_level: float = 0.3,
        dry_level: float = 0.7
    ) -> AudioSegment:
        """Aplica efeito de reverberação."""
        # Converte para numpy
        samples = np.array(audio.get_array_of_samples())
        
        # Aplica reverb
        reverb = np.zeros_like(samples, dtype=np.float32)
        decay = np.exp(-damping * np.arange(len(samples)))
        
        for i in range(len(samples)):
            if i < room_size * len(samples):
                reverb[i] = samples[i]
            else:
                idx = int(i - room_size * len(samples))
                reverb[i] = samples[i] * dry_level + \
                           samples[idx] * wet_level * decay[i-idx]
                           
        # Converte de volta
        return AudioSegment(
            reverb.tobytes(),
            frame_rate=audio.frame_rate,
            sample_width=audio.sample_width,
            channels=audio.channels
        )
        
    def _apply_eq(
        self,
        audio: AudioSegment,
        low_gain: float = 1.0,
        mid_gain: float = 1.0,
        high_gain: float = 1.0
    ) -> AudioSegment:
        """Aplica equalização de 3 bandas."""
        # Frequências de corte
        low_shelf = 200   # Hz
        high_shelf = 2000 # Hz
        
        # Aplica filtros
        audio = audio.low_shelf_filter(
            low_shelf,
            gain=low_gain
        )
        
        audio = audio.high_shelf_filter(
            high_shelf,
            gain=high_gain
        )
        
        # Ganho médio
        return audio + (mid_gain - 1.0) * 10
        
    async def get_duration(self, audio_path: str) -> float:
        """
        Obtém duração do áudio em segundos.
        
        Args:
            audio_path: Caminho do arquivo
            
        Returns:
            Duração em segundos
        """
        try:
            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0
            
        except Exception as e:
            logger.error(f"Erro obtendo duração: {e}")
            raise 