"""
Endpoints para geração de vídeos usando FastHuayuan.
Suporta geração de vídeos com diferentes modelos e estilos.
"""

from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile
from src.api.v2.schemas.requests.video import VideoGenerationRequest
from src.api.v2.schemas.responses.video import VideoGenerationResponse
from src.core.gpu.manager import gpu_manager
from src.core.queue.manager import queue_manager
from src.core.cache.manager import cache_manager
from src.services.thumbnails import thumbnail_service
from pydantic import BaseModel, Field
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

router = APIRouter()
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

@router.post("/generate", response_model=VideoGenerationResponse)
async def generate_video(
    request: VideoGenerationRequest,
    background_tasks: BackgroundTasks,
):
    """
    Gera um vídeo usando FastHuayuan baseado nos parâmetros fornecidos.
    
    Args:
        request: Parâmetros para geração do vídeo
        background_tasks: Tarefas em background do FastAPI
    
    Returns:
        VideoGenerationResponse: Status da geração e ID da tarefa
    
    Raises:
        HTTPException: Se houver erro na validação ou na geração
    """
    try:
        # Verifica disponibilidade de GPU
        gpu = await gpu_manager.get_available_gpu(
            min_vram=12000  # Requer mais VRAM para vídeo
        )
        if not gpu:
            raise HTTPException(
                status_code=503,
                detail="Nenhuma GPU com VRAM suficiente disponível"
            )
        
        # Cria tarefa na fila
        task_id = await queue_manager.enqueue_task(
            task_type="video_generation",
            params=request.dict(),
            gpu_id=gpu.id,
            priority=request.priority
        )
        
        # Inicia processamento em background
        background_tasks.add_task(
            gpu_manager.process_task,
            task_id=task_id,
            gpu_id=gpu.id
        )
        
        return VideoGenerationResponse(
            task_id=task_id,
            status="queued",
            estimated_time=await gpu_manager.estimate_completion_time(
                gpu.id,
                task_type="video"
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar vídeo: {str(e)}"
        )

@router.get("/status/{task_id}", response_model=VideoGenerationResponse)
async def get_generation_status(task_id: str):
    """
    Retorna o status atual de uma tarefa de geração de vídeo.
    
    Args:
        task_id: ID da tarefa de geração
    
    Returns:
        VideoGenerationResponse: Status atual da geração
    
    Raises:
        HTTPException: Se a tarefa não for encontrada
    """
    try:
        # Busca status no cache
        status = await cache_manager.get(f"task:{task_id}")
        if not status:
            raise HTTPException(
                status_code=404,
                detail="Tarefa não encontrada"
            )
            
        # Se o vídeo foi concluído e não tem preview, gera o thumbnail
        if (
            status.get("status") == "completed" 
            and status.get("result_url") 
            and not status.get("preview_url")
        ):
            video_path = status["result_url"]
            try:
                thumbnail_path, _ = await thumbnail_service.get_or_generate(
                    video_path,
                    animated=True,
                    duration=3.0,
                    fps=10
                )
                status["preview_url"] = thumbnail_path
                await cache_manager.set(f"task:{task_id}", status)
            except Exception as e:
                # Não falha se o thumbnail não puder ser gerado
                print(f"Erro ao gerar thumbnail: {str(e)}")
            
        return VideoGenerationResponse(**status)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar status: {str(e)}"
        )

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