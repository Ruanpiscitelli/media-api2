"""
Modelos Pydantic para entidades relacionadas a vozes.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

class Voice(BaseModel):
    """Modelo para uma voz no sistema."""
    
    id: Optional[str] = None
    name: str
    description: str
    language: str
    gender: str
    model_path: str
    config_path: str
    preview_url: str
    tags: List[str] = []
    capabilities: Dict = Field(default_factory=lambda: {
        "emotions": ["neutral"],
        "speed_range": [0.5, 2.0],
        "pitch_range": [-10, 10]
    })
    samples: List[Dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class VoiceCloneRequest(BaseModel):
    """Modelo para uma requisição de clonagem de voz."""
    
    name: str
    description: str
    language: str
    gender: str
    sample_paths: List[str]
    transcriptions: List[str]
    settings: Dict = Field(default_factory=lambda: {
        "quality": "high",
        "preserve_pronunciation": True
    })

class VoiceCloneStatus(BaseModel):
    """Modelo para o status de um processo de clonagem."""
    
    clone_id: str
    status: str = "processing"  # processing, completed, failed
    progress: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None
    voice_id: Optional[str] = None
    preview_url: Optional[str] = None
    error: Optional[str] = None
    request: Optional[VoiceCloneRequest] = None

class VoiceGenerationRequest(BaseModel):
    """Modelo para uma requisição de geração de voz."""
    
    text: str
    voice_id: str
    emotion: str = "neutral"
    speed: float = 1.0
    pitch: float = 0.0
    volume: float = 1.0
    preserve_characteristics: bool = True
    audio_effects: Dict = Field(default_factory=dict)

class VoiceGenerationResponse(BaseModel):
    """Modelo para resposta de geração de voz."""
    
    id: str
    url: str
    duration: float
    text: str
    metadata: Dict
    created_at: datetime = Field(default_factory=datetime.now)

class BatchVoiceGenerationRequest(BaseModel):
    """Modelo para requisição de geração em lote."""
    
    items: List[VoiceGenerationRequest]
    output_format: str = "mp3"
    quality: str = "high"

class BatchVoiceGenerationResponse(BaseModel):
    """Modelo para resposta de geração em lote."""
    
    items: List[VoiceGenerationResponse]
    total_duration: float
    created_at: datetime = Field(default_factory=datetime.now) 