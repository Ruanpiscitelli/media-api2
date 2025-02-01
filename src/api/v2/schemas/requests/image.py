"""
Schemas para requisições de geração de imagens.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class ImageGenerationRequest(BaseModel):
    """
    Modelo para requisição de geração de imagem.
    """
    prompt: str = Field(
        ...,
        description="Prompt descritivo para geração da imagem",
        min_length=1,
        max_length=1000
    )
    
    negative_prompt: Optional[str] = Field(
        None,
        description="Prompt negativo para evitar elementos indesejados",
        max_length=1000
    )
    
    width: int = Field(
        1024,
        description="Largura da imagem em pixels",
        ge=512,
        le=2048
    )
    
    height: int = Field(
        1024,
        description="Altura da imagem em pixels",
        ge=512,
        le=2048
    )
    
    num_inference_steps: int = Field(
        25,
        description="Número de passos de inferência",
        ge=1,
        le=100
    )
    
    guidance_scale: float = Field(
        7.5,
        description="Escala de guidance do modelo",
        ge=1.0,
        le=20.0
    )
    
    priority: int = Field(
        1,
        description="Prioridade da tarefa (1-5, sendo 5 a mais alta)",
        ge=1,
        le=5
    )
    
    style_preset: Optional[str] = Field(
        None,
        description="Preset de estilo pré-definido"
    )
    
    lora_weights: Optional[List[str]] = Field(
        None,
        description="Lista de pesos LoRA a serem aplicados"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "prompt": "Um gato siamês dormindo em uma almofada azul, estilo realista",
                "negative_prompt": "distorção, baixa qualidade, pixelado",
                "width": 1024,
                "height": 1024,
                "num_inference_steps": 25,
                "guidance_scale": 7.5,
                "priority": 1,
                "style_preset": "realistic",
                "lora_weights": ["cat_v1", "realistic_v2"]
            }
        } 