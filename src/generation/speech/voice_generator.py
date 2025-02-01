"""
Gerador de voz usando Fish Speech.
Responsável pela síntese de voz com suporte a diferentes vozes e emoções.
"""

import logging
from typing import Dict, Optional
import os
import torch
import torchaudio
from transformers import AutoModelForSpeechSeq2Seq

logger = logging.getLogger(__name__)

class VoiceGenerator:
    """
    Gerador de voz usando Fish Speech.
    Suporta múltiplas vozes, emoções e estilos.
    """
    
    def __init__(
        self,
        model_path: str,
        device: str = "cuda",
        voice_embeddings_path: str = "models/voices"
    ):
        """
        Inicializa o gerador de voz.
        
        Args:
            model_path: Caminho para o modelo Fish Speech
            device: Dispositivo para inferência ('cuda' ou 'cpu')
            voice_embeddings_path: Caminho para embeddings de vozes
        """
        self.device = device
        self.model = self._load_model(model_path)
        self.voice_embeddings = self._load_voice_embeddings(voice_embeddings_path)
        
    def _load_model(self, model_path: str) -> AutoModelForSpeechSeq2Seq:
        """Carrega o modelo Fish Speech."""
        try:
            model = AutoModelForSpeechSeq2Seq.from_pretrained(model_path)
            model = model.to(self.device)
            model.eval()
            return model
            
        except Exception as e:
            logger.error(f"Erro carregando modelo: {e}")
            raise
            
    def _load_voice_embeddings(self, path: str) -> Dict[str, torch.Tensor]:
        """
        Carrega embeddings de vozes disponíveis.
        
        Args:
            path: Caminho para diretório com embeddings
            
        Returns:
            Dicionário com embeddings por ID de voz
        """
        embeddings = {}
        try:
            for file in os.listdir(path):
                if file.endswith(".pt"):
                    voice_id = file.replace(".pt", "")
                    embedding = torch.load(
                        os.path.join(path, file),
                        map_location=self.device
                    )
                    embeddings[voice_id] = embedding
                    
            return embeddings
            
        except Exception as e:
            logger.error(f"Erro carregando embeddings: {e}")
            raise
            
    def generate_speech(
        self,
        processed_text: Dict,
        voice_id: str,
        emotion: str = "neutral",
        speed: float = 1.0,
        pitch: float = 0.0,
        volume: float = 1.0
    ) -> torch.Tensor:
        """
        Gera áudio a partir do texto processado.
        
        Args:
            processed_text: Texto processado com tokens e prosódia
            voice_id: ID da voz a ser usada
            emotion: Emoção desejada
            speed: Velocidade da fala (1.0 = normal)
            pitch: Ajuste de tom (-10.0 a 10.0)
            volume: Volume da voz (1.0 = normal)
            
        Returns:
            Tensor com áudio gerado
        """
        try:
            # Prepara entrada
            phonemes = torch.tensor(
                processed_text['phonemes'],
                device=self.device
            )
            
            # Obtém embeddings
            voice_embedding = self._get_voice_embedding(voice_id)
            emotion_embedding = self._get_emotion_embedding(emotion)
            
            # Combina embeddings
            combined_embedding = self._combine_embeddings(
                voice_embedding,
                emotion_embedding
            )
            
            # Gera áudio base
            with torch.no_grad():
                audio = self.model.generate(
                    phonemes.unsqueeze(0),
                    voice_embedding=combined_embedding,
                    do_sample=True,
                    max_length=1000,
                    temperature=0.7
                )
            
            # Aplica transformações
            audio = self._apply_transformations(
                audio.squeeze(0),
                speed=speed,
                pitch=pitch,
                volume=volume
            )
            
            return audio
            
        except Exception as e:
            logger.error(f"Erro na geração de voz: {e}")
            raise
            
    def _get_voice_embedding(self, voice_id: str) -> torch.Tensor:
        """Obtém embedding para uma voz específica."""
        if voice_id not in self.voice_embeddings:
            raise ValueError(f"Voz não encontrada: {voice_id}")
            
        return self.voice_embeddings[voice_id]
        
    def _get_emotion_embedding(self, emotion: str) -> torch.Tensor:
        """
        Obtém embedding para uma emoção específica.
        
        Args:
            emotion: Nome da emoção
            
        Returns:
            Tensor com embedding da emoção
        """
        emotion_vectors = {
            "neutral": [0.0, 0.0, 0.0],
            "happy": [0.5, 0.3, 0.2],
            "sad": [-0.3, -0.2, -0.1],
            "angry": [0.4, -0.3, 0.1],
            "excited": [0.7, 0.4, 0.3]
        }
        
        vector = emotion_vectors.get(emotion, emotion_vectors["neutral"])
        return torch.tensor(vector, device=self.device)
        
    def _combine_embeddings(
        self,
        voice_embedding: torch.Tensor,
        emotion_embedding: torch.Tensor
    ) -> torch.Tensor:
        """
        Combina embeddings de voz e emoção.
        
        Args:
            voice_embedding: Embedding da voz
            emotion_embedding: Embedding da emoção
            
        Returns:
            Embedding combinado
        """
        # Normaliza embeddings
        voice_embedding = torch.nn.functional.normalize(voice_embedding, dim=0)
        emotion_embedding = torch.nn.functional.normalize(emotion_embedding, dim=0)
        
        # Combina com peso para emoção
        combined = voice_embedding + 0.3 * emotion_embedding
        
        return torch.nn.functional.normalize(combined, dim=0)
        
    def _apply_transformations(
        self,
        audio: torch.Tensor,
        speed: float = 1.0,
        pitch: float = 0.0,
        volume: float = 1.0
    ) -> torch.Tensor:
        """
        Aplica transformações no áudio gerado.
        
        Args:
            audio: Tensor com áudio
            speed: Fator de velocidade
            pitch: Ajuste de tom
            volume: Fator de volume
            
        Returns:
            Áudio transformado
        """
        try:
            # Ajusta velocidade
            if speed != 1.0:
                audio = torchaudio.transforms.Speed(speed)(audio)
            
            # Ajusta tom
            if pitch != 0.0:
                audio = torchaudio.transforms.PitchShift(
                    sample_rate=44100,
                    n_steps=pitch
                )(audio)
            
            # Ajusta volume
            if volume != 1.0:
                audio = audio * volume
            
            return audio
            
        except Exception as e:
            logger.error(f"Erro aplicando transformações: {e}")
            return audio  # Retorna áudio original em caso de erro