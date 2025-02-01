"""
Endpoints para gerenciamento e uso de templates de mídia.
Suporta templates para redes sociais, banners, watermarks e mais.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, File, UploadFile, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import json
import io
import os
from datetime import datetime
from PIL import Image

from src.core.text_engine import text_engine
from src.core.image_engine import image_engine
from src.api.v2.schemas.templates import (
    TemplateDefinition,
    TemplateMetadata,
    TemplateCreateRequest,
    TemplateUpdateRequest,
    TemplateListResponse,
    TemplateVersionsResponse,
    TemplateVersionInfo
)
from src.comfy.template_manager import TemplateManager
from src.comfy.default_templates import get_default_templates
from src.services.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["Templates"])

# Instância do gerenciador (deve ser inicializada na startup da aplicação)
template_manager = TemplateManager()

# Schemas
class TemplateModification(BaseModel):
    """Modificação a ser aplicada em um template."""
    name: str
    type: str = "text"  # text, image, shape, filter
    text: Optional[str] = None
    image_url: Optional[str] = None
    font: Optional[str] = None
    size: Optional[float] = None
    color: Optional[tuple[int, int, int]] = None
    position: Optional[tuple[int, int]] = None
    dimensions: Optional[tuple[int, int]] = None
    opacity: Optional[float] = 1.0
    rotation: Optional[float] = 0.0
    effects: Optional[List[Dict[str, Any]]] = None

class TemplateRequest(BaseModel):
    """Requisição para geração de imagem a partir de template."""
    template_id: str
    modifications: List[TemplateModification]
    output_format: str = "png"
    quality: int = Field(80, ge=1, le=100)
    webhook_url: Optional[str] = None

class Template(BaseModel):
    """Template para geração de imagens."""
    id: str
    name: str
    description: Optional[str] = None
    width: int
    height: int
    layers: List[Dict[str, Any]]
    category: Optional[str] = None
    tags: List[str] = []

# Cache de templates
templates: Dict[str, Template] = {}

# Endpoints
@router.post("/generate")
async def generate_from_template(
    request: TemplateRequest,
    background_tasks: BackgroundTasks
):
    """
    Gera uma imagem a partir de um template com modificações especificadas.
    Similar ao Bannerbear, permite modificar textos, imagens e elementos do template.
    
    Args:
        request: Dados do template e modificações
        background_tasks: Tarefas em background
        
    Returns:
        URL da imagem gerada e metadados
    """
    try:
        # Carregar template
        template = await load_template(request.template_id)
        if not template:
            raise HTTPException(
                status_code=404,
                detail="Template não encontrado"
            )
        
        # Criar imagem base
        image = await create_base_image(template)
        
        # Aplicar modificações
        for mod in request.modifications:
            if mod.type == "text":
                await apply_text_modification(image, mod)
            elif mod.type == "image":
                await apply_image_modification(image, mod)
            elif mod.type == "shape":
                await apply_shape_modification(image, mod)
            elif mod.type == "filter":
                await apply_filter_modification(image, mod)
                
        # Otimizar e salvar
        output_url = await save_and_optimize(
            image,
            format=request.output_format,
            quality=request.quality
        )
        
        # Webhook se especificado
        if request.webhook_url:
            background_tasks.add_task(
                send_webhook,
                request.webhook_url,
                {
                    "status": "completed",
                    "url": output_url
                }
            )
            
        return {
            "status": "success",
            "url": output_url,
            "template_id": request.template_id,
            "format": request.output_format
        }
        
    except Exception as e:
        logger.error(f"Erro gerando a partir do template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=TemplateDefinition)
async def create_template(
    request: TemplateCreateRequest,
    current_user = Depends(get_current_user)
):
    """
    Cria um novo template.
    """
    try:
        template = template_manager.create_template(
            name=request.name,
            description=request.description,
            workflow=request.workflow,
            parameters=request.parameters,
            parameter_mappings=request.parameter_mappings,
            author=current_user.username,
            tags=request.tags,
            category=request.category
        )
        return template
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
@router.get("/")
async def list_templates(current_user = Depends(get_current_user)):
    return {"templates": []}
        
@router.get("/{name}", response_model=TemplateDefinition)
async def get_template(
    name: str,
    version: Optional[str] = None
):
    """
    Obtém um template específico.
    """
    try:
        return template_manager.get_template(name, version)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@router.put("/{name}", response_model=TemplateDefinition)
async def update_template(
    name: str,
    request: TemplateUpdateRequest,
    current_user = Depends(get_current_user)
):
    """
    Atualiza um template existente.
    """
    try:
        return template_manager.update_template(
            name=name,
            description=request.description,
            workflow=request.workflow,
            parameters=request.parameters,
            parameter_mappings=request.parameter_mappings,
            tags=request.tags,
            category=request.category,
            author=current_user.username
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@router.delete("/{name}")
async def delete_template(
    name: str,
    version: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Remove um template.
    """
    try:
        template_manager.delete_template(name, version)
        return JSONResponse(content={"message": "Template removido com sucesso"})
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@router.get("/{name}/versions", response_model=TemplateVersionsResponse)
async def get_template_versions(name: str):
    """
    Lista versões de um template.
    """
    try:
        versions = template_manager.get_template_versions(name)
        return TemplateVersionsResponse(
            template_name=name,
            versions=versions
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@router.post("/{name}/apply", response_model=Dict[str, Any])
async def apply_template(
    name: str,
    parameters: Dict[str, Any],
    version: Optional[str] = None
):
    """
    Aplica parâmetros em um template.
    """
    try:
        # Carrega template
        template = template_manager.get_template(name, version)
        
        # Aplica parâmetros
        workflow = template_manager.apply_parameters(template, parameters)
        
        return workflow
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initialize", response_model=Dict[str, Any])
async def initialize_templates(
    current_user = Depends(get_current_user)
):
    """
    Inicializa os templates padrão do sistema.
    Requer autenticação de usuário.
    """
    try:
        templates = get_default_templates()
        results = {
            "success": [],
            "errors": []
        }
        
        for template_data in templates:
            try:
                template = template_manager.create_template(
                    name=template_data["name"],
                    description=template_data["description"],
                    workflow=template_data["workflow"],
                    parameters=template_data["parameters"],
                    parameter_mappings=template_data["parameter_mappings"],
                    author="system",
                    tags=template_data["tags"],
                    category=template_data["category"]
                )
                results["success"].append(template_data["name"])
            except ValueError as e:
                results["errors"].append({
                    "template": template_data["name"],
                    "error": str(e)
                })
                
        return {
            "message": "Templates inicializados",
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro inicializando templates: {str(e)}"
        )

# Funções auxiliares
async def load_template(template_id: str) -> Optional[Template]:
    """Carrega um template do cache."""
    return templates.get(template_id)

async def create_base_image(template: Template) -> Image.Image:
    """Cria a imagem base do template."""
    try:
        # Criar imagem vazia
        image = Image.new(
            "RGBA",
            (template.width, template.height),
            (0, 0, 0, 0)
        )
        
        # Aplicar camadas base
        for layer in template.layers:
            if layer.get("type") == "background":
                color = layer.get("color", (0, 0, 0))
                image = Image.new(
                    "RGBA",
                    (template.width, template.height),
                    color
                )
                break
                
        return image
    except Exception as e:
        logger.error(f"Erro criando imagem base: {e}")
        raise

async def apply_text_modification(image: Image.Image, mod: TemplateModification):
    """Aplica modificação de texto na imagem."""
    result = text_engine.process_text(
        text=mod.text,
        font_name=mod.font,
        size=mod.size,
        color=mod.color
    )
    
    # Compor texto na posição especificada
    if mod.position:
        image.paste(
            result["image"],
            mod.position,
            result["image"]
        )

async def apply_image_modification(image: Image.Image, mod: TemplateModification):
    """Aplica modificação de imagem na imagem base."""
    if mod.image_url:
        overlay = await download_image(mod.image_url)
        
        if mod.dimensions:
            overlay = image_engine.process_image(
                overlay,
                operations=[{
                    "type": "resize",
                    "params": {
                        "width": mod.dimensions[0],
                        "height": mod.dimensions[1]
                    }
                }]
            )
            
        if mod.position:
            image.paste(
                overlay,
                mod.position,
                overlay if overlay.mode == 'RGBA' else None
            )

async def apply_shape_modification(image: Image.Image, mod: TemplateModification):
    """Aplica modificação de forma na imagem."""
    # TODO: Implementar shapes (retângulos, círculos, etc)
    pass

async def apply_filter_modification(image: Image.Image, mod: TemplateModification):
    """Aplica filtros na imagem."""
    if mod.effects:
        for effect in mod.effects:
            image = image_engine.process_image(
                image,
                operations=[{
                    "type": "effect",
                    "params": effect
                }]
            )

async def save_and_optimize(
    image: Image.Image,
    format: str = "png",
    quality: int = 80
) -> str:
    """Salva e otimiza a imagem, retornando URL."""
    # TODO: Implementar salvamento real em CDN/storage
    return "https://api.example.com/images/123.png"

async def send_webhook(url: str, data: dict):
    """Envia webhook com resultado da geração."""
    # TODO: Implementar envio real de webhook
    pass 