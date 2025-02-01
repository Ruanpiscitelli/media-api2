"""
Schemas para respostas de geração de imagens.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ImageGenerationResponse(BaseModel):
    """
    Modelo para resposta de geração de imagem.
    """
    task_id: str = Field(
        ...,
        description="ID único da tarefa de geração"
    )
    
    status: str = Field(
        ...,
        description="Status atual da tarefa",
        examples=["queued", "processing", "completed", "failed"]
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
    
    result_url: Optional[str] = Field(
        None,
        description="URL da imagem gerada (disponível quando status=completed)"
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
                "estimated_time": 15.5,
                "progress": 45.0,
                "created_at": "2024-01-20T10:30:00Z",
                "updated_at": "2024-01-20T10:30:15Z",
                "gpu_info": {
                    "id": "gpu0",
                    "model": "RTX 4090",
                    "vram_usage": "8.5GB/24GB"
                }
            }
        } 