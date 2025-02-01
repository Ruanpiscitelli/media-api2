"""
Schemas para respostas de geração de vídeos.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class VideoGenerationResponse(BaseModel):
    """
    Modelo para resposta de geração de vídeo.
    """
    task_id: str = Field(
        ...,
        description="ID único da tarefa de geração"
    )
    
    status: str = Field(
        ...,
        description="Status atual da tarefa",
        examples=["queued", "processing", "rendering", "completed", "failed"]
    )
    
    estimated_time: Optional[float] = Field(
        None,
        description="Tempo estimado para conclusão em segundos"
    )
    
    progress: Optional[float] = Field(
        None,
        description="Progresso da geração (0-100%)",
        ge=0,
        le=100
    )
    
    frames_completed: Optional[int] = Field(
        None,
        description="Número de frames já processados"
    )
    
    total_frames: Optional[int] = Field(
        None,
        description="Número total de frames a serem processados"
    )
    
    result_url: Optional[str] = Field(
        None,
        description="URL do vídeo gerado (disponível quando status=completed)"
    )
    
    preview_url: Optional[str] = Field(
        None,
        description="URL de preview do vídeo (thumbnail ou gif)"
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
                "estimated_time": 120.5,
                "progress": 35.0,
                "frames_completed": 52,
                "total_frames": 150,
                "preview_url": "https://api.example.com/media/preview/550e8400.gif",
                "created_at": "2024-01-20T10:30:00Z",
                "updated_at": "2024-01-20T10:31:15Z",
                "gpu_info": {
                    "id": "gpu0",
                    "model": "RTX 4090",
                    "vram_usage": "18.5GB/24GB"
                }
            }
        } 