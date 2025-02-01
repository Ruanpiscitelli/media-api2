"""
Endpoints para geração e manipulação de imagens.
"""

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Query, Body
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.core.auth import get_current_user
from src.services.image import ImageService
from src.core.gpu.manager import GPUManager
from src.core.rate_limit import rate_limiter

router = APIRouter(prefix="/generate/image", tags=["Geração de Imagem"])

class ImageGenerationRequest(BaseModel):
    """
    Modelo para requisição de geração de imagem.
    
    Attributes:
        prompt: Descrição textual da imagem desejada
        negative_prompt: Elementos que não devem aparecer na imagem
        width: Largura da imagem em pixels
        height: Altura da imagem em pixels
        num_inference_steps: Número de passos de inferência
        guidance_scale: Escala de orientação do modelo
        seed: Seed para reprodutibilidade (opcional)
        style_preset: Preset de estilo a ser aplicado (opcional)
    """
    prompt: str = Field(..., description="Descrição textual da imagem desejada")
    negative_prompt: Optional[str] = Field(None, description="Elementos a serem evitados")
    width: int = Field(1024, description="Largura em pixels", ge=512, le=2048)
    height: int = Field(1024, description="Altura em pixels", ge=512, le=2048)
    num_inference_steps: int = Field(30, description="Passos de inferência", ge=1, le=100)
    guidance_scale: float = Field(7.5, description="Escala de orientação", ge=1.0, le=20.0)
    seed: Optional[int] = Field(None, description="Seed para reprodutibilidade")
    style_preset: Optional[str] = Field(None, description="Preset de estilo")

class ImageGenerationResponse(BaseModel):
    """
    Modelo para resposta de geração de imagem.
    
    Attributes:
        id: Identificador único da geração
        url: URL da imagem gerada
        metadata: Metadados da geração
        created_at: Data/hora da geração
    """
    id: str = Field(..., description="ID da geração")
    url: HttpUrl = Field(..., description="URL da imagem")
    metadata: Dict[str, Any] = Field(..., description="Metadados")
    created_at: datetime = Field(..., description="Data/hora da geração")

class ImageStyle(BaseModel):
    """
    Modelo para estilo de imagem.
    
    Attributes:
        id: Identificador do estilo
        name: Nome amigável do estilo
        description: Descrição do estilo
        preview_url: URL de preview do estilo
    """
    id: str = Field(..., description="ID do estilo")
    name: str = Field(..., description="Nome do estilo")
    description: str = Field(..., description="Descrição")
    preview_url: Optional[HttpUrl] = Field(None, description="URL de preview")

@router.post(
    "",
    response_model=ImageGenerationResponse,
    summary="Gerar Imagem",
    description="""
    Gera uma imagem a partir de uma descrição textual usando SDXL.
    
    Features:
    - Controle preciso de dimensões
    - Prompt negativo para exclusão de elementos
    - Ajuste de passos de inferência e guidance
    - Suporte a seeds para reprodutibilidade
    - Presets de estilo pré-configurados
    """,
    responses={
        200: {
            "description": "Imagem gerada com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "id": "img_123",
                        "url": "http://exemplo.com/images/123.png",
                        "metadata": {
                            "prompt": "uma paisagem futurista",
                            "width": 1024,
                            "height": 1024
                        },
                        "created_at": "2024-01-30T12:00:00Z"
                    }
                }
            }
        },
        400: {
            "description": "Parâmetros inválidos",
            "content": {
                "application/json": {
                    "example": {"detail": "Dimensões inválidas"}
                }
            }
        },
        429: {
            "description": "Limite de requisições excedido",
            "content": {
                "application/json": {
                    "example": {"detail": "Muitas requisições. Aguarde alguns segundos."}
                }
            }
        }
    }
)
async def generate_image(
    request: ImageGenerationRequest,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """Gera uma imagem a partir do prompt fornecido."""
    try:
        image_service = ImageService()
        result = await image_service.generate(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            width=request.width,
            height=request.height,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            seed=request.seed,
            style_preset=request.style_preset,
            user_id=current_user.id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/styles",
    response_model=List[ImageStyle],
    summary="Listar Estilos",
    description="Retorna lista de estilos pré-configurados disponíveis.",
    responses={
        200: {
            "description": "Lista de estilos obtida com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "styles": [
                            {
                                "id": "futuristic",
                                "name": "Futurista",
                                "description": "Estilo futurista e sci-fi",
                                "preview_url": "http://exemplo.com/styles/futuristic.jpg"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def list_styles():
    """Lista todos os estilos disponíveis."""
    try:
        image_service = ImageService()
        styles = await image_service.get_styles()
        return styles
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/history",
    summary="Histórico de Gerações",
    description="Retorna histórico de imagens geradas pelo usuário.",
    responses={
        200: {
            "description": "Histórico obtido com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "generations": [
                            {
                                "id": "img_123",
                                "url": "http://exemplo.com/images/123.png",
                                "prompt": "paisagem futurista",
                                "created_at": "2024-01-30T12:00:00Z"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_history(
    limit: int = Query(10, description="Número máximo de registros", ge=1, le=100),
    offset: int = Query(0, description="Offset para paginação", ge=0),
    current_user = Depends(get_current_user)
):
    """Obtém histórico de gerações do usuário."""
    try:
        image_service = ImageService()
        history = await image_service.get_user_history(
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        return {"generations": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 