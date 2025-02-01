"""
Processador de áudio para pós-processamento de voz sintetizada.
Inclui normalização, efeitos e melhorias de qualidade.
"""

import logging
from typing import Dict, Optional
import torch
import torchaudio
import torchaudio.transforms as T
import torch.nn.functional as F

logger = logging.getLogger(__name__)

class AudioNormalizer:
    """Normalização de áudio."""
    
    def normalize(
        self,
        audio: torch.Tensor,
        target_db: float = -20.0
    ) -> torch.Tensor:
        """
        Normaliza o volume do áudio para um nível alvo.
        
        Args:
            audio: Tensor com áudio
            target_db: Nível alvo em dB
            
        Returns:
            Áudio normalizado
        """
        try:
            # Calcula RMS atual
            rms = torch.sqrt(torch.mean(audio ** 2))
            current_db = 20 * torch.log10(rms)
            
            # Calcula ganho necessário
            gain = 10 ** ((target_db - current_db) / 20)
            
            return audio * gain
            
        except Exception as e:
            logger.error(f"Erro na normalização: {e}")
            return audio


class AudioEffects:
    """Processador de efeitos de áudio."""
    
    def add_reverb(
        self,
        audio: torch.Tensor,
        room_size: float = 0.5,
        damping: float = 0.5,
        wet_level: float = 0.3,
        dry_level: float = 0.7
    ) -> torch.Tensor:
        """
        Adiciona reverberação ao áudio.
        
        Args:
            audio: Tensor com áudio
            room_size: Tamanho da sala (0.0 a 1.0)
            damping: Amortecimento (0.0 a 1.0)
            wet_level: Nível do efeito (0.0 a 1.0)
            dry_level: Nível do áudio original (0.0 a 1.0)
            
        Returns:
            Áudio com reverberação
        """
        try:
            # Cria impulso da sala
            decay = int(room_size * 44100)  # Baseado no sample rate
            impulse = torch.exp(-torch.arange(decay).float() * damping)
            
            # Aplica convolução
            reverb = F.conv1d(
                audio.unsqueeze(0).unsqueeze(0),
                impulse.unsqueeze(0).unsqueeze(0),
                padding=decay
            ).squeeze()
            
            # Mistura sinal seco e molhado
            return dry_level * audio + wet_level * reverb
            
        except Exception as e:
            logger.error(f"Erro ao adicionar reverb: {e}")
            return audio
            
    def apply_eq(
        self,
        audio: torch.Tensor,
        low_gain: float = 1.0,
        mid_gain: float = 1.0,
        high_gain: float = 1.0
    ) -> torch.Tensor:
        """
        Aplica equalização de 3 bandas.
        
        Args:
            audio: Tensor com áudio
            low_gain: Ganho para baixas frequências
            mid_gain: Ganho para médias frequências
            high_gain: Ganho para altas frequências
            
        Returns:
            Áudio equalizado
        """
        try:
            # Frequências de corte
            low_cut = 300  # Hz
            high_cut = 3000  # Hz
            
            # Filtros
            low_pass = torchaudio.transforms.LowpassBiquad(
                sample_rate=44100,
                cutoff_freq=low_cut
            )
            
            band_pass = torchaudio.transforms.BandpassBiquad(
                sample_rate=44100,
                central_freq=(low_cut + high_cut) / 2,
                Q=1.0
            )
            
            high_pass = torchaudio.transforms.HighpassBiquad(
                sample_rate=44100,
                cutoff_freq=high_cut
            )
            
            # Aplica filtros e ganhos
            low = low_pass(audio) * low_gain
            mid = band_pass(audio) * mid_gain
            high = high_pass(audio) * high_gain
            
            # Combina bandas
            return low + mid + high
            
        except Exception as e:
            logger.error(f"Erro ao aplicar EQ: {e}")
            return audio
            
    def compress(
        self,
        audio: torch.Tensor,
        threshold: float = -20.0,
        ratio: float = 4.0,
        attack: float = 0.005,
        release: float = 0.1
    ) -> torch.Tensor:
        """
        Aplica compressão dinâmica.
        
        Args:
            audio: Tensor com áudio
            threshold: Limiar em dB
            ratio: Taxa de compressão
            attack: Tempo de ataque em segundos
            release: Tempo de liberação em segundos
            
        Returns:
            Áudio comprimido
        """
        try:
            # Calcula envelope
            abs_audio = torch.abs(audio)
            envelope = torch.zeros_like(audio)
            
            # Constantes de tempo
            attack_coef = torch.exp(-1 / (44100 * attack))
            release_coef = torch.exp(-1 / (44100 * release))
            
            # Calcula envelope
            for i in range(len(audio)):
                if abs_audio[i] > envelope[i-1]:
                    envelope[i] = attack_coef * envelope[i-1] + \
                        (1 - attack_coef) * abs_audio[i]
                else:
                    envelope[i] = release_coef * envelope[i-1] + \
                        (1 - release_coef) * abs_audio[i]
            
            # Calcula ganho
            level_db = 20 * torch.log10(envelope + 1e-10)
            gain_db = torch.min(
                torch.zeros_like(level_db),
                (threshold - level_db) * (1 - 1/ratio)
            )
            gain = 10 ** (gain_db / 20)
            
            return audio * gain
            
        except Exception as e:
            logger.error(f"Erro ao comprimir: {e}")
            return audio


class AudioEnhancer:
    """Melhorias de qualidade de áudio."""
    
    def enhance(
        self,
        audio: torch.Tensor,
        noise_reduction: float = 0.1,
        clarity: float = 1.2
    ) -> torch.Tensor:
        """
        Aplica melhorias de qualidade.
        
        Args:
            audio: Tensor com áudio
            noise_reduction: Intensidade da redução de ruído
            clarity: Fator de clareza
            
        Returns:
            Áudio melhorado
        """
        try:
            # Redução de ruído espectral
            spec = torch.stft(
                audio,
                n_fft=2048,
                hop_length=512,
                window=torch.hann_window(2048),
                return_complex=True
            )
            
            # Estima ruído do espectro
            noise_floor = torch.mean(torch.abs(spec), dim=1, keepdim=True)
            
            # Aplica redução
            gain = (1 - noise_reduction) + \
                noise_reduction * (torch.abs(spec) > noise_floor)
            spec = spec * gain
            
            # Melhora clareza
            spec = spec * (torch.abs(spec) ** (clarity - 1))
            
            # Volta para domínio do tempo
            audio = torch.istft(
                spec,
                n_fft=2048,
                hop_length=512,
                window=torch.hann_window(2048)
            )
            
            return audio
            
        except Exception as e:
            logger.error(f"Erro ao melhorar áudio: {e}")
            return audio


class AudioProcessor:
    """
    Processador completo de áudio.
    Combina normalização, efeitos e melhorias.
    """
    
    def __init__(self):
        self.normalizer = AudioNormalizer()
        self.effects = AudioEffects()
        self.enhancer = AudioEnhancer()
        
    def process_audio(
        self,
        audio: torch.Tensor,
        sample_rate: int = 44100,
        effects: Optional[Dict] = None
    ) -> torch.Tensor:
        """
        Processa o áudio aplicando todos os efeitos necessários.
        
        Args:
            audio: Tensor com áudio
            sample_rate: Taxa de amostragem
            effects: Dicionário com parâmetros de efeitos
            
        Returns:
            Áudio processado
        """
        try:
            # Normalização básica
            audio = self.normalizer.normalize(audio)
            
            # Aplica efeitos se especificados
            if effects:
                audio = self._apply_effects(audio, effects)
                
            # Melhora qualidade
            audio = self.enhancer.enhance(audio)
            
            return audio
            
        except Exception as e:
            logger.error(f"Erro no processamento de áudio: {e}")
            return audio
            
    def _apply_effects(self, audio: torch.Tensor, effects: Dict) -> torch.Tensor:
        """
        Aplica efeitos específicos ao áudio.
        
        Args:
            audio: Tensor com áudio
            effects: Dicionário com parâmetros de efeitos
            
        Returns:
            Áudio com efeitos aplicados
        """
        try:
            for effect, params in effects.items():
                if effect == "reverb":
                    audio = self.effects.add_reverb(audio, **params)
                elif effect == "eq":
                    audio = self.effects.apply_eq(audio, **params)
                elif effect == "compression":
                    audio = self.effects.compress(audio, **params)
                    
            return audio
            
        except Exception as e:
            logger.error(f"Erro aplicando efeitos: {e}")
            return audio