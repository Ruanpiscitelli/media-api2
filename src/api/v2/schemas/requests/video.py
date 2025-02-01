"""
Schemas para requisições de geração de vídeos.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator

class VideoGenerationRequest(BaseModel):
    """
    Modelo para requisição de geração de vídeo.
    """
    prompt: str = Field(
        ...,
        description="Prompt descritivo para geração do vídeo",
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
        description="Largura do vídeo em pixels",
        ge=512,
        le=2048
    )
    
    height: int = Field(
        1024,
        description="Altura do vídeo em pixels",
        ge=512,
        le=2048
    )
    
    duration: float = Field(
        5.0,
        description="Duração do vídeo em segundos",
        ge=1.0,
        le=30.0
    )
    
    fps: int = Field(
        30,
        description="Frames por segundo",
        ge=15,
        le=60
    )
    
    motion_scale: float = Field(
        1.0,
        description="Escala de movimento (1.0 = normal)",
        ge=0.1,
        le=2.0
    )
    
    num_inference_steps: int = Field(
        25,
        description="Número de passos de inferência por frame",
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
                "prompt": "Um pássaro voando sobre um lago ao pôr do sol, estilo cinematográfico",
                "negative_prompt": "distorção, baixa qualidade, pixelado",
                "width": 1024,
                "height": 1024,
                "duration": 5.0,
                "fps": 30,
                "motion_scale": 1.0,
                "num_inference_steps": 25,
                "guidance_scale": 7.5,
                "priority": 1,
                "style_preset": "cinematic",
                "lora_weights": ["nature_v1", "cinematic_v2"]
            }
        }

class VideoElement(BaseModel):
    """Elemento de vídeo (texto, imagem, forma etc)."""
    type: str = Field(..., description="Tipo do elemento (text, image, shape)")
    content: Dict[str, Any] = Field(..., description="Configuração do elemento")
    start_time: float = Field(0, description="Tempo inicial em segundos", ge=0)
    duration: Optional[float] = Field(None, description="Duração em segundos", ge=0)
    position: Any = Field("center", description="Posição do elemento")
    effects: Optional[List[Dict[str, Any]]] = None

    @validator("type")
    def validate_type(cls, v):
        valid_types = ["text", "image", "shape"]
        if v not in valid_types:
            raise ValueError(f"Tipo inválido. Deve ser um de: {valid_types}")
        return v

    @validator("effects")
    def validate_effects(cls, v):
        if v:
            valid_effects = ["fade_in", "fade_out", "blur", "rotate"]
            for effect in v:
                if "type" not in effect:
                    raise ValueError("Efeito deve ter um tipo")
                if effect["type"] not in valid_effects:
                    raise ValueError(f"Tipo de efeito inválido. Deve ser um de: {valid_effects}")
        return v

class VideoScene(BaseModel):
    """Cena de vídeo com elementos e transições."""
    duration: float = Field(..., description="Duração da cena em segundos", gt=0, le=3600)
    background: Optional[Dict[str, Any]] = None
    elements: List[VideoElement] = Field(default_factory=list)
    transition: Optional[Dict[str, Any]] = None

    @validator("background")
    def validate_background(cls, v):
        if v:
            valid_types = ["color", "image", "video"]
            if "type" not in v:
                raise ValueError("Background deve ter um tipo")
            if v["type"] not in valid_types:
                raise ValueError(f"Tipo de background inválido. Deve ser um de: {valid_types}")
            
            if v["type"] == "color":
                if "color" not in v:
                    raise ValueError("Background de cor deve ter uma cor especificada")
            elif v["type"] == "image":
                if "image" not in v:
                    raise ValueError("Background de imagem deve ter um caminho de imagem")
            elif v["type"] == "video":
                if "video" not in v:
                    raise ValueError("Background de vídeo deve ter um caminho de vídeo")
        return v

    @validator("transition")
    def validate_transition(cls, v):
        if v:
            valid_types = ["fade", "slide", "wipe"]
            if "type" not in v:
                raise ValueError("Transição deve ter um tipo")
            if v["type"] not in valid_types:
                raise ValueError(f"Tipo de transição inválido. Deve ser um de: {valid_types}")
            
            if "duration" in v:
                if not isinstance(v["duration"], (int, float)):
                    raise ValueError("Duração da transição deve ser um número")
                if v["duration"] <= 0 or v["duration"] > 10:
                    raise ValueError("Duração da transição deve estar entre 0 e 10 segundos")
        return v

class VideoProject(BaseModel):
    """Projeto de vídeo completo."""
    width: int = Field(..., description="Largura do vídeo", gt=0, le=3840)  # Máximo 4K
    height: int = Field(..., description="Altura do vídeo", gt=0, le=2160)  # Máximo 4K
    fps: int = Field(30, description="Frames por segundo", ge=1, le=60)
    scenes: List[VideoScene] = Field(..., description="Cenas do vídeo")
    audio: Optional[Dict[str, Any]] = None
    output_format: str = Field("mp4", description="Formato de saída")

    @validator("scenes")
    def validate_scenes(cls, v):
        if not v:
            raise ValueError("Projeto deve ter pelo menos uma cena")
        total_duration = sum(scene.duration for scene in v)
        if total_duration > 3600:  # Máximo 1 hora
            raise ValueError("Duração total do vídeo não pode exceder 1 hora")
        return v

    @validator("output_format")
    def validate_output_format(cls, v):
        valid_formats = ["mp4", "webm", "mov"]
        if v not in valid_formats:
            raise ValueError(f"Formato de saída inválido. Deve ser um de: {valid_formats}")
        return v

    @validator("audio")
    def validate_audio(cls, v):
        if v:
            valid_types = ["file", "tts"]
            if "type" not in v:
                raise ValueError("Configuração de áudio deve ter um tipo")
            if v["type"] not in valid_types:
                raise ValueError(f"Tipo de áudio inválido. Deve ser um de: {valid_types}")
            
            if v["type"] == "file":
                if "file" not in v:
                    raise ValueError("Áudio do tipo file deve ter um caminho de arquivo")
            elif v["type"] == "tts":
                if "text" not in v:
                    raise ValueError("Áudio TTS deve ter um texto")
        return v 