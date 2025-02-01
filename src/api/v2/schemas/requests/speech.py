"""
Schemas para requisições de síntese de voz.
"""

from typing import Optional
from pydantic import BaseModel, Field

class SpeechSynthesisRequest(BaseModel):
    """
    Modelo para requisição de síntese de voz.
    """
    text: str = Field(
        ...,
        description="Texto a ser sintetizado em voz",
        min_length=1,
        max_length=5000
    )
    
    voice_id: str = Field(
        ...,
        description="ID da voz a ser utilizada",
        examples=["female_1", "male_1", "child_1"]
    )
    
    language: str = Field(
        "pt-BR",
        description="Código do idioma (ISO 639-1)",
        examples=["pt-BR", "en-US", "es-ES"]
    )
    
    emotion: Optional[str] = Field(
        "neutral",
        description="Emoção da voz",
        examples=["neutral", "happy", "sad", "angry"]
    )
    
    speed: float = Field(
        1.0,
        description="Velocidade da fala (1.0 = normal)",
        ge=0.5,
        le=2.0
    )
    
    pitch: float = Field(
        0.0,
        description="Ajuste de tom (-10.0 a 10.0, 0 = normal)",
        ge=-10.0,
        le=10.0
    )
    
    volume: float = Field(
        1.0,
        description="Volume da voz (1.0 = normal)",
        ge=0.1,
        le=2.0
    )
    
    priority: int = Field(
        1,
        description="Prioridade da tarefa (1-5, sendo 5 a mais alta)",
        ge=1,
        le=5
    )
    
    audio_format: str = Field(
        "wav",
        description="Formato do arquivo de áudio",
        examples=["wav", "mp3", "ogg"]
    )
    
    sample_rate: int = Field(
        44100,
        description="Taxa de amostragem em Hz",
        examples=[22050, 44100, 48000]
    )
    
    class Config:
        schema_extra = {
            "example": {
                "text": "Olá, como você está? Espero que esteja tendo um ótimo dia!",
                "voice_id": "female_1",
                "language": "pt-BR",
                "emotion": "happy",
                "speed": 1.1,
                "pitch": 0.0,
                "volume": 1.0,
                "priority": 1,
                "audio_format": "wav",
                "sample_rate": 44100
            }
        } 