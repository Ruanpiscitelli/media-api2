"""
Endpoints para geração e edição de vídeos.
"""

from typing import List, Dict, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, Query, Body
from src.api.v2.schemas.requests.video import VideoGenerationRequest
from src.api.v2.schemas.responses.video import VideoGenerationResponse
from src.core.gpu.manager import gpu_manager, GPUManager
from src.core.queue.manager import queue_manager
from src.core.cache.manager import cache_manager
from src.services.thumbnails import thumbnail_service
from pydantic import BaseModel, Field, HttpUrl
import tempfile
import os
from pathlib import Path
import logging
from src.video.composition_system import VideoCompositionSystem
from src.video.templates import TemplateManager
from src.core.auth import get_current_user
from src.core.rate_limit import rate_limiter
from src.services.video import VideoService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate/video", tags=["Geração de Vídeo"])
video_system = VideoCompositionSystem()
template_manager = TemplateManager()
video_service = VideoService()

# Modelos Pydantic
class VideoRequest(BaseModel):
    """Modelo para requisição de criação de vídeo"""
    composition_type: str  # "slideshow", "overlay", "composite"
    resources: Dict
    settings: Dict
    output_format: str = "mp4"
    
class SlideshowRequest(BaseModel):
    """Modelo para requisição de criação de slideshow"""
    duration: float = 5.0
    transition: str = "fade"
    template: Optional[str] = None
    template_customization: Optional[Dict] = None
    
class VideoResponse(BaseModel):
    """Modelo para resposta de criação de vídeo"""
    status: str
    video_url: str
    duration: float
    format: str

class VideoElement(BaseModel):
    """Elemento de uma cena do vídeo"""
    type: str = Field(..., description="Tipo do elemento (text, image, video)")
    content: str = Field(..., description="Conteúdo do elemento")
    position: Dict[str, float] = Field(
        default={"x": 0.5, "y": 0.5},
        description="Posição do elemento (x,y de 0 a 1)"
    )
    style: Optional[Dict] = Field(
        default={},
        description="Estilos do elemento (fonte, cor, etc)"
    )

class VideoScene(BaseModel):
    """Cena do vídeo"""
    duration: float = Field(..., description="Duração da cena em segundos")
    elements: List[VideoElement] = Field(..., description="Elementos da cena")
    transition: Optional[Dict] = Field(
        default={"type": "fade", "duration": 0.5},
        description="Transição para próxima cena"
    )

class VideoAudio(BaseModel):
    """Configuração de áudio do vídeo"""
    text: Optional[str] = Field(None, description="Texto para narração")
    voice_id: Optional[str] = Field(None, description="ID da voz para narração")
    music_url: Optional[str] = Field(None, description="URL da música de fundo")
    volume: Optional[Dict[str, float]] = Field(
        default={"narration": 1.0, "music": 0.3},
        description="Volumes dos elementos de áudio"
    )

class Json2VideoRequest(BaseModel):
    """Requisição para geração de vídeo"""
    scenes: List[VideoScene] = Field(..., description="Cenas do vídeo")
    audio: Optional[VideoAudio] = Field(None, description="Configuração de áudio")
    format: str = Field(
        default="mp4",
        description="Formato do vídeo (mp4, webm)"
    )
    quality: str = Field(
        default="high",
        description="Qualidade do vídeo (low, medium, high)"
    )

class VideoEditRequest(BaseModel):
    """
    Modelo para requisição de edição de vídeo.
    
    Attributes:
        operations: Lista de operações a serem aplicadas
        output_format: Formato de saída desejado
        quality: Qualidade do vídeo de saída
    """
    operations: List[Dict[str, Any]] = Field(..., description="Operações de edição")
    output_format: str = Field("mp4", description="Formato de saída")
    quality: str = Field("high", description="Qualidade do vídeo")

@router.post(
    "",
    response_model=VideoGenerationResponse,
    summary="Gerar Vídeo",
    description="""
    Gera um vídeo a partir de uma descrição textual.
    
    Features:
    - Geração frame-a-frame com controle de movimento
    - Suporte a áudio gerado por IA
    - Múltiplos presets de estilo
    - Controle de dimensões e FPS
    """,
    responses={
        200: {
            "description": "Vídeo em geração",
            "content": {
                "application/json": {
                    "example": {
                        "id": "vid_123",
                        "status": "processing",
                        "progress": 0,
                        "estimated_time": 120
                    }
                }
            }
        },
        400: {
            "description": "Parâmetros inválidos"
        },
        429: {
            "description": "Limite de requisições excedido"
        },
        503: {
            "description": "Recursos GPU não disponíveis"
        }
    }
)
async def generate_video(
    request: VideoGenerationRequest,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """Inicia geração de vídeo."""
    try:
        # Estimar VRAM necessária baseado nos parâmetros do vídeo
        required_vram = request.width * request.height * request.num_frames * 4  # Estimativa básica em bytes
        required_vram = max(required_vram, 4 * 1024 * 1024 * 1024)  # Mínimo 4GB VRAM
        
        # Verificar disponibilidade de GPU
        gpu = await gpu_manager.get_available_gpu(min_vram=required_vram)
        if not gpu:
            raise HTTPException(
                status_code=503,
                detail="Nenhuma GPU com VRAM suficiente disponível no momento"
            )

        video_service = VideoService()
        result = await video_service.generate(
            prompt=request.prompt,
            num_frames=request.num_frames,
            fps=request.fps,
            motion_scale=request.motion_scale,
            width=request.width,
            height=request.height,
            audio_prompt=request.audio_prompt,
            style_preset=request.style_preset,
            user_id=current_user.id,
            gpu_id=gpu.id  # Passa o ID da GPU alocada
        )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro na geração do vídeo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/status/{video_id}",
    response_model=VideoGenerationResponse,
    summary="Status da Geração",
    description="Retorna o status atual de uma geração de vídeo.",
    responses={
        200: {
            "description": "Status obtido com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "id": "vid_123",
                        "status": "completed",
                        "progress": 100,
                        "url": "http://exemplo.com/videos/123.mp4",
                        "preview_url": "http://exemplo.com/videos/123_preview.gif"
                    }
                }
            }
        },
        404: {
            "description": "Vídeo não encontrado"
        }
    }
)
async def get_video_status(
    video_id: str,
    current_user = Depends(get_current_user)
):
    """Obtém status de uma geração de vídeo."""
    try:
        video_service = VideoService()
        status = await video_service.get_status(video_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post(
    "/edit",
    summary="Editar Vídeo",
    description="""
    Aplica operações de edição em um vídeo existente.
    
    Operações suportadas:
    - Corte temporal
    - Redimensionamento
    - Filtros e efeitos
    - Adição de áudio
    - Transições
    """,
    responses={
        200: {
            "description": "Edição iniciada com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "edit_123",
                        "status": "processing"
                    }
                }
            }
        }
    }
)
async def edit_video(
    video_id: str,
    request: VideoEditRequest,
    current_user = Depends(get_current_user)
):
    """Aplica edições em um vídeo."""
    try:
        video_service = VideoService()
        result = await video_service.edit(
            video_id=video_id,
            operations=request.operations,
            output_format=request.output_format,
            quality=request.quality,
            user_id=current_user.id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/merge",
    summary="Mesclar Vídeos",
    description="Combina múltiplos vídeos em um único vídeo.",
    responses={
        200: {
            "description": "Mesclagem iniciada com sucesso"
        }
    }
)
async def merge_videos(
    video_ids: List[str],
    transition_type: Optional[str] = "fade",
    current_user = Depends(get_current_user)
):
    """Mescla múltiplos vídeos."""
    try:
        video_service = VideoService()
        result = await video_service.merge(
            video_ids=video_ids,
            transition_type=transition_type,
            user_id=current_user.id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/v2/video/create", response_model=VideoResponse)
async def create_video(
    request: VideoRequest,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """
    Cria um vídeo baseado na composição fornecida
    """
    try:
        result = await video_system.create_complex_composition(
            request.resources,
            request.settings,
            request.output_format
        )
        
        return {
            "status": "success",
            "video_url": result['url'],
            "duration": result['duration'],
            "format": result['format']
        }
        
    except Exception as e:
        logger.error(f"Erro na criação do vídeo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/v2/video/slideshow", response_model=VideoResponse)
async def create_slideshow(
    images: List[UploadFile] = File(...),
    request: SlideshowRequest = None,
    audio: Optional[UploadFile] = None,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """
    Cria um slideshow a partir de imagens enviadas
    """
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Salvar imagens
            image_paths = []
            for img in images:
                temp_path = os.path.join(temp_dir, img.filename)
                with open(temp_path, "wb") as f:
                    f.write(await img.read())
                image_paths.append(temp_path)
                
            # Salvar áudio se fornecido
            audio_path = None
            if audio:
                audio_path = os.path.join(temp_dir, audio.filename)
                with open(audio_path, "wb") as f:
                    f.write(await audio.read())
                    
            # Aplicar template se especificado
            settings = {}
            if request and request.template:
                template = template_manager.get_template(request.template)
                if request.template_customization:
                    template = template_manager.customize_template(
                        request.template,
                        request.template_customization
                    )
                settings = template
                
            # Criar slideshow
            result = await video_system.create_slideshow(
                image_paths,
                duration=request.duration if request else 5.0,
                transition=request.transition if request else "fade",
                audio_path=audio_path,
                settings=settings
            )
            
            return {
                "status": "success",
                "video_url": result['url'],
                "duration": result['duration'],
                "format": "mp4"
            }
            
    except Exception as e:
        logger.error(f"Erro na criação do slideshow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/v2/video/overlay", response_model=VideoResponse)
async def create_video_with_overlay(
    base_video: UploadFile = File(...),
    overlay_video: UploadFile = File(...),
    position: Dict = None,
    timing: Dict = None,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """
    Cria um vídeo com overlay
    """
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Salvar vídeos
            base_path = os.path.join(temp_dir, base_video.filename)
            with open(base_path, "wb") as f:
                f.write(await base_video.read())
                
            overlay_path = os.path.join(temp_dir, overlay_video.filename)
            with open(overlay_path, "wb") as f:
                f.write(await overlay_video.read())
                
            # Criar vídeo com overlay
            result = await video_system.create_video_with_overlay(
                base_path,
                overlay_path,
                position or {'x': 0, 'y': 0},
                timing or {'start': 0, 'end': 10},
                os.path.join(temp_dir, "output.mp4")
            )
            
            return {
                "status": "success",
                "video_url": result['url'],
                "duration": result['duration'],
                "format": "mp4"
            }
            
    except Exception as e:
        logger.error(f"Erro na criação do vídeo com overlay: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/v2/video/templates")
async def list_templates(
    current_user = Depends(get_current_user)
):
    """
    Lista templates disponíveis
    """
    try:
        templates = template_manager.get_template_names()
        return {
            "status": "success",
            "templates": templates
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/v2/video/template/{template_name}")
async def get_template_info(
    template_name: str,
    current_user = Depends(get_current_user)
):
    """
    Retorna informações sobre um template
    """
    try:
        template_info = template_manager.get_template_info(template_name)
        return {
            "status": "success",
            "template": template_info
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter informações do template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/json2video/create", response_model=VideoResponse)
async def create_video(
    request: Json2VideoRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """
    Cria vídeo a partir de especificação JSON.
    Processa em background e retorna ID do projeto.
    """
    try:
        # Validar projeto
        project = await video_service.validate_project(request.scenes)
        
        # Estimar recursos
        resources = await video_service.estimate_resources(request.dict())
        
        # Verificar GPU disponível
        gpu = await gpu_manager.get_available_gpu(
            min_vram=resources['vram_required']
        )
        
        if not gpu:
            raise HTTPException(
                status_code=503,
                detail="Nenhuma GPU com VRAM suficiente disponível"
            )
            
        # Criar tarefa
        task_id = await queue_manager.enqueue_task(
            task_type="video_generation",
            params=request.dict(),
            gpu_id=gpu.id,
            priority=2
        )
        
        # Processar em background
        background_tasks.add_task(
            video_service.process_video_project,
            task_id=task_id,
            gpu_id=gpu.id
        )
        
        return {
            "project_id": task_id,
            "status": "processing",
            "progress": 0,
            "estimated_time": await video_service.estimate_completion_time(
                task_id,
                resources
            )
        }
        
    except Exception as e:
        logger.error(f"Erro criando vídeo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/json2video/{project_id}/status", response_model=VideoResponse)
async def get_video_status(
    project_id: str,
    current_user = Depends(get_current_user)
):
    """Retorna status atual do projeto"""
    try:
        status = await video_service.get_project_status(project_id)
        return status
        
    except Exception as e:
        logger.error(f"Erro obtendo status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/json2video/{project_id}/preview")
async def generate_preview(
    project_id: str,
    scene_index: int,
    time: float,
    current_user = Depends(get_current_user)
):
    """Gera preview de uma cena em um momento específico"""
    try:
        preview = await video_service.generate_preview(
            project_id,
            scene_index,
            time
        )
        return preview
    except Exception as e:
        logger.error(f"Erro gerando preview: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 