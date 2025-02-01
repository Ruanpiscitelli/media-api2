"""
Modelo MusicGen do Suno AI para geração de música.
"""

import torch
import torchaudio
import logging
from typing import Dict, Optional, List
from transformers import AutoProcessor, MusicgenForConditionalGeneration
import numpy as np

logger = logging.getLogger(__name__)

class MusicGenModel:
    """Modelo para geração de música usando MusicGen."""
    
    def __init__(self, model_name: str, device: torch.device):
        """
        Inicializa o modelo.
        
        Args:
            model_name: Nome do modelo no HuggingFace
            device: Dispositivo para execução (CPU/GPU)
        """
        self.model_name = model_name
        self.device = device
        self.model = None
        self.processor = None
        
    async def load(self):
        """Carrega o modelo e processador."""
        try:
            logger.info(f"Carregando modelo {self.model_name}")
            
            # Carregar processador
            self.processor = AutoProcessor.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32
            )
            
            # Carregar modelo
            self.model = MusicgenForConditionalGeneration.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32
            )
            
            # Mover para GPU se disponível
            self.model.to(self.device)
            
            # Otimizações
            if self.device.type == "cuda":
                self.model = torch.compile(self.model)
            
            logger.info("Modelo carregado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro carregando modelo: {e}")
            raise
            
    async def generate(
        self,
        prompt: str,
        duration: int = 30,
        style: Optional[str] = None,
        tempo: Optional[int] = None,
        key: Optional[str] = None,
        instruments: Optional[List[str]] = None,
        options: Optional[Dict] = None
    ) -> torch.Tensor:
        """
        Gera música baseada nos parâmetros.
        
        Args:
            prompt: Descrição da música
            duration: Duração em segundos
            style: Estilo musical
            tempo: BPM
            key: Tom musical
            instruments: Lista de instrumentos
            options: Opções avançadas
            
        Returns:
            Tensor com áudio gerado
        """
        try:
            # Construir prompt completo
            full_prompt = prompt
            if style:
                full_prompt += f" Style: {style}."
            if tempo:
                full_prompt += f" Tempo: {tempo} BPM."
            if key:
                full_prompt += f" Key: {key}."
            if instruments:
                full_prompt += f" Instruments: {', '.join(instruments)}."
                
            # Processar prompt
            inputs = self.processor(
                text=[full_prompt],
                padding=True,
                return_tensors="pt"
            )
            
            # Mover para GPU
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Configurar parâmetros de geração
            generation_config = {
                "max_new_tokens": int(duration * 50),  # Aproximadamente
                "do_sample": True,
                "guidance_scale": 3.0,
                "temperature": options.get("temperature", 0.7),
                "top_k": options.get("top_k", 50),
                "top_p": options.get("top_p", 0.95)
            }
            
            # Gerar música
            with torch.cuda.amp.autocast():
                outputs = self.model.generate(
                    **inputs,
                    **generation_config
                )
            
            # Processar saída
            audio = outputs.audio[0].cpu()
            
            # Normalizar
            audio = audio / torch.abs(audio).max()
            
            return audio
            
        except Exception as e:
            logger.error(f"Erro gerando música: {e}")
            raise
            
    def _prepare_reference(
        self,
        reference_audio: str,
        sample_rate: int = 44100
    ) -> torch.Tensor:
        """
        Prepara áudio de referência.
        
        Args:
            reference_audio: Caminho do áudio
            sample_rate: Taxa de amostragem
            
        Returns:
            Tensor com áudio processado
        """
        try:
            # Carregar áudio
            waveform, sr = torchaudio.load(reference_audio)
            
            # Converter para mono se necessário
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Resample se necessário
            if sr != sample_rate:
                resampler = torchaudio.transforms.Resample(sr, sample_rate)
                waveform = resampler(waveform)
            
            # Normalizar
            waveform = waveform / torch.abs(waveform).max()
            
            return waveform
            
        except Exception as e:
            logger.error(f"Erro processando áudio de referência: {e}")
            raise 