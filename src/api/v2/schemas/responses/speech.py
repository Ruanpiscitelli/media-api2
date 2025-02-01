"""
Schemas para respostas de síntese de voz.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class SpeechSynthesisResponse(BaseModel):
    """
    Modelo para resposta de síntese de voz.
    """
    task_id: str = Field(
        ...,
        description="ID único da tarefa de síntese"
    )
    
    status: str = Field(
        ...,
        description="Status atual da tarefa",
        examples=["queued", "processing", "encoding", "completed", "failed"]
    )
    
    estimated_time: Optional[float] = Field(
        None,
        description="Tempo estimado para conclusão em segundos"
    )
    
    progress: Optional[float] = Field(
        None,
        description="Progresso da síntese (0-100%)",
        ge=0,
        le=100
    )
    
    duration: Optional[float] = Field(
        None,
        description="Duração do áudio em segundos"
    )
    
    file_size: Optional[int] = Field(
        None,
        description="Tamanho do arquivo em bytes"
    )
    
    result_url: Optional[str] = Field(
        None,
        description="URL do áudio sintetizado (disponível quando status=completed)"
    )
    
    waveform_url: Optional[str] = Field(
        None,
        description="URL da visualização da forma de onda do áudio"
    )
    
    error: Optional[str] = Field(
        None,
        description="Mensagem de erro (disponível quando status=failed)"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data e hora de criação da tarefa"
    )
    
    updated_at: Optional[datetime] = Field(
        None,
        description="Data e hora da última atualização"
    )
    
    gpu_info: Optional[dict] = Field(
        None,
        description="Informações sobre a GPU utilizada"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "estimated_time": 5.5,
                "progress": 60.0,
                "duration": 12.5,
                "file_size": 245760,
                "waveform_url": "https://api.example.com/media/waveform/550e8400.png",
                "created_at": "2024-01-20T10:30:00Z",
                "updated_at": "2024-01-20T10:30:03Z",
                "gpu_info": {
                    "id": "gpu0",
                    "model": "RTX 4090",
                    "vram_usage": "4.5GB/24GB"
                }
            }
        } 