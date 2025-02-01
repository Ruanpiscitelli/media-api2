"""
Processador de áudio.
"""

import io
import uuid
import logging
import numpy as np
from pathlib import Path
from typing import List, Optional, Union

import torch
import torchaudio
import soundfile as sf
from pydub import AudioSegment
from pydub.silence import split_on_silence

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Classe para processamento de áudio."""
    
    def __init__(self):
        self.sample_rate = 44100
        self.channels = 2
        
    def load_audio(self, file_path: Union[str, Path]) -> Optional[torch.Tensor]:
        """
        Carrega arquivo de áudio de forma síncrona.
        
        Args:
            file_path: Caminho do arquivo de áudio
            
        Returns:
            Tensor do PyTorch contendo o áudio ou None se houver erro
        """
        try:
            waveform, sample_rate = torchaudio.load(file_path)
            if sample_rate != self.sample_rate:
                waveform = torchaudio.functional.resample(
                    waveform, 
                    sample_rate, 
                    self.sample_rate
                )
            return waveform
        except Exception as e:
            logger.error(f"Erro ao carregar áudio: {e}")
            return None
            
    def save_audio(self, waveform: torch.Tensor, file_path: Union[str, Path]) -> bool:
        """
        Salva tensor como arquivo de áudio de forma síncrona.
        
        Args:
            waveform: Tensor contendo o áudio
            file_path: Caminho onde salvar o arquivo
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        try:
            torchaudio.save(
                file_path,
                waveform,
                self.sample_rate,
                channels_first=True
            )
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar áudio: {e}")
            return False

    def concatenate(
        self,
        audio_paths: List[Union[str, Path]],
        crossfade: float = 0.3,
        format: str = "wav"
    ) -> Optional[str]:
        """
        Concatena múltiplos arquivos de áudio com crossfade.
        
        Args:
            audio_paths: Lista de caminhos dos arquivos
            crossfade: Duração do crossfade em segundos
            format: Formato do arquivo de saída
        
        Returns:
            Caminho do arquivo concatenado ou None se houver erro
        """
        try:
            segments = [AudioSegment.from_file(str(path)) for path in audio_paths]
            
            crossfade_ms = int(crossfade * 1000)
            
            final_audio = segments[0]
            for segment in segments[1:]:
                final_audio = final_audio.append(segment, crossfade=crossfade_ms)
                
            final_audio = final_audio.normalize()
            
            output_path = f"outputs/speech/concat_{uuid.uuid4()}.{format}"
            
            final_audio.export(
                output_path,
                format=format,
                parameters=["-ac", "1"]
            )
            
            return output_path
            
        except Exception as e:
            logger.error(f"Erro concatenando áudios: {e}")
            return None

    def prepare_for_streaming(
        self,
        audio_path: Union[str, Path],
        chunk_size: int = 4096,
        format: str = "wav"
    ) -> Optional[bytes]:
        """
        Prepara áudio para streaming.
            
        Args:
            audio_path: Caminho do arquivo
            chunk_size: Tamanho do chunk em bytes
            format: Formato do áudio
            
        Returns:
            Chunk de áudio em bytes ou None se houver erro
        """
        try:
            waveform = self.load_audio(audio_path)
            if waveform is None:
                return None
                
            buffer = io.BytesIO()
            
            sf.write(
                buffer,
                waveform.numpy().T,
                self.sample_rate,
                format=format,
                subtype='PCM_16'
            )
            
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Erro preparando áudio para streaming: {e}")
            return None

    def apply_effects(
        self,
        audio_path: Union[str, Path],
        effects: Optional[dict] = None
    ) -> Optional[str]:
        """
        Aplica efeitos no áudio.
        
        Args:
            audio_path: Caminho do arquivo
            effects: Dicionário com efeitos a aplicar
            
        Returns:
            Caminho do arquivo processado ou None se houver erro
        """
        try:
            if not effects:
                return str(audio_path)
                
            audio = AudioSegment.from_file(str(audio_path))
            
            if effects.get('normalize'):
                audio = audio.normalize()
                
            if effects.get('remove_silence'):
                audio = self._remove_silence(audio)
                
            output_path = f"outputs/speech/processed_{uuid.uuid4()}.wav"
            audio.export(output_path, format="wav")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Erro aplicando efeitos: {e}")
            return None

    def get_duration(self, audio_path: Union[str, Path]) -> Optional[float]:
        """
        Obtém duração do áudio em segundos.
        
        Args:
            audio_path: Caminho do arquivo
            
        Returns:
            Duração em segundos ou None se houver erro
        """
        try:
            audio = AudioSegment.from_file(str(audio_path))
            return len(audio) / 1000.0
            
        except Exception as e:
            logger.error(f"Erro obtendo duração: {e}")
            return None

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