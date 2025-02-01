"""
Processamento de áudio
"""
import numpy as np
import torch
import torchaudio
from typing import Optional

class AudioProcessor:
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate
        
    def validate_audio(self, audio: torch.Tensor) -> bool:
        """Valida tensor de áudio"""
        try:
            # Verificar dimensões
            if audio.dim() != 2:
                raise ValueError(
                    f"Áudio deve ter 2 dimensões, tem {audio.dim()}"
                )
                
            # Verificar canais
            if audio.size(0) > 2:
                raise ValueError(
                    f"Máximo 2 canais, tem {audio.size(0)}"
                )
                
            # Verificar sample rate
            if audio.size(1) / self.sample_rate > 60:
                raise ValueError(
                    "Áudio muito longo (max 60 segundos)"
                )
                
            # Verificar valores
            if torch.isnan(audio).any():
                raise ValueError("Áudio contém NaN")
                
            return True
            
        except Exception as e:
            logger.error(f"Erro validando áudio: {e}")
            return False 