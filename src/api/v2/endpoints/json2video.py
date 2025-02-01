"""
Endpoints para geração de vídeo a partir de JSON.
Permite criar vídeos dinâmicos com base em templates e modificações.
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator
import asyncio
import json
import os
from datetime import datetime
from threading import Lock
from asyncio import Semaphore
from collections import OrderedDict
from shlex import quote
import re
import uuid  # Add UUID import

from src.core.video_engine import video_engine
from src.core.audio_engine import audio_engine
from src.core.config import settings
from src.services.comfy_server import comfy_server

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/json2video", tags=["json2video"])

# Configurações
MAX_CONCURRENT_RENDERS = settings.MAX_CONCURRENT_RENDERS
RENDER_TIMEOUT = settings.RENDER_TIMEOUT_SECONDS
MAX_CACHED_STATUS = 1000

# Semáforo para limitar renderizações concorrentes
render_semaphore = Semaphore(MAX_CONCURRENT_RENDERS)

class RenderStatusManager:
    """Gerenciador thread-safe de status de renderização."""
    
    def __init__(self, max_cache: int = MAX_CACHED_STATUS):
        self._status = OrderedDict()
        self._lock = Lock()
        self._max_cache = max_cache
        
    def set(self, project_id: str, status: 'RenderProgress'):
        """Atualiza status de forma thread-safe."""
        with self._lock:
            self._status[project_id] = status
            # Limpar cache se necessário
            while len(self._status) > self._max_cache:
                self._status.popitem(first=True)
                
    def get(self, project_id: str) -> Optional['RenderProgress']:
        """Obtém status de forma thread-safe."""
        with self._lock:
            return self._status.get(project_id)
            
    def remove(self, project_id: str):
        """Remove status de forma thread-safe."""
        with self._lock:
            self._status.pop(project_id, None)

# Instância global do gerenciador de status
status_manager = RenderStatusManager()

# Modelos Pydantic
class VideoElement(BaseModel):
    """Elemento de vídeo (texto, imagem, forma etc)."""
    type: str = Field(..., description="Tipo do elemento (text, image, shape)")
    content: Dict[str, Any] = Field(..., description="Configuração do elemento")
    start_time: float = Field(0, description="Tempo inicial em segundos")
    duration: Optional[float] = None
    position: Any = Field("center", description="Posição do elemento")
    effects: Optional[List[Dict[str, Any]]] = None

class VideoScene(BaseModel):
    """Cena de vídeo com elementos e transições."""
    duration: float = Field(..., description="Duração da cena em segundos")
    background: Optional[Dict[str, Any]] = None
    elements: List[VideoElement] = Field(default_factory=list)
    transition: Optional[Dict[str, Any]] = None

class VideoProject(BaseModel):
    """Projeto de vídeo completo."""
    width: int = Field(..., description="Largura do vídeo")
    height: int = Field(..., description="Altura do vídeo")
    fps: int = Field(30, description="Frames por segundo")
    scenes: List[VideoScene] = Field(..., description="Cenas do vídeo")
    audio: Optional[Dict[str, Any]] = None
    output_format: str = Field("mp4", description="Formato de saída")

    @validator("scenes")
    def validate_scenes(cls, v):
        if not v:
            raise ValueError("Projeto deve ter pelo menos uma cena")
        return v

class RenderProgress(BaseModel):
    """Status do processo de renderização."""
    project_id: str
    status: str = Field(..., description="Status (queued, rendering, completed, failed)")
    progress: float = Field(0, description="Progresso (0-100)")
    output_url: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

@router.post("/projects", response_model=RenderProgress)
async def create_project(
    project: VideoProject,
    background_tasks: BackgroundTasks
):
    """
    Cria um novo projeto de vídeo e inicia a renderização.
    
    Args:
        project: Configuração do projeto
        background_tasks: Gerenciador de tarefas em background
        
    Returns:
        Status inicial da renderização
    """
    try:
        # Gerar ID único
        project_id = f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Criar status inicial
        status = RenderProgress(
            project_id=project_id,
            status="queued",
            progress=0
        )
        status_manager.set(project_id, status)
        
        # Iniciar renderização em background
        background_tasks.add_task(
            render_project,
            project_id,
            project
        )
        
        return status
    except Exception as e:
        logger.error(f"Erro criando projeto: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}", response_model=RenderProgress)
async def get_project_status(project_id: str):
    """
    Retorna o status de renderização de um projeto.
    
    Args:
        project_id: ID do projeto
        
    Returns:
        Status atual da renderização
    """
    try:
        status = status_manager.get(project_id)
        if not status:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")
            
        return status
    except Exception as e:
        logger.error(f"Erro obtendo status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/preview")
async def generate_preview(scene: VideoScene):
    """
    Gera um preview de uma cena.
    
    Args:
        scene: Configuração da cena
        
    Returns:
        URL do preview gerado como GIF animado
    """
    try:
        # Gerar ID único para o preview usando UUID v4 e timestamp com microsegundos
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        unique_id = str(uuid.uuid4())[:8]  # Usando primeiros 8 caracteres do UUID
        preview_id = f"preview_{timestamp}_{unique_id}"
        
        # Configurar tamanho reduzido para preview
        preview_width = 480
        preview_height = 270
        preview_fps = 15
        
        # Criar clip da cena em tamanho reduzido
        clip = await video_engine.create_scene(
            width=preview_width,
            height=preview_height,
            duration=min(scene.duration, 10.0),  # Limitar a 10 segundos
            fps=preview_fps,
            background=scene.background
        )
        
        # Adicionar elementos
        for element in scene.elements:
            # Ajustar posição e tamanho para preview
            if isinstance(element.position, dict):
                for key in element.position:
                    if isinstance(element.position[key], (int, float)):
                        element.position[key] *= (preview_width / 1920)  # Assumindo 1920 como base
            
            if "size" in element.content:
                if isinstance(element.content["size"], (int, float)):
                    element.content["size"] *= (preview_width / 1920)
                elif isinstance(element.content["size"], dict):
                    for key in element.content["size"]:
                        if isinstance(element.content["size"][key], (int, float)):
                            element.content["size"][key] *= (preview_width / 1920)
            
            clip = await video_engine.add_element(
                clip,
                element.content,
                element.start_time
            )
        
        # Gerar GIF animado
        output_path = f"static/previews/{preview_id}.gif"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        await video_engine.export_gif(
            clip,
            output_path,
            fps=preview_fps,
            optimize=True
        )
        
        # Retornar URL do preview
        return {
            "preview_url": f"/static/previews/{preview_id}.gif",
            "width": preview_width,
            "height": preview_height,
            "duration": min(scene.duration, 10.0)
        }
        
    except Exception as e:
        logger.error(f"Erro gerando preview: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro gerando preview: {str(e)}"
        )

async def validate_ffmpeg_params(params: dict):
    """Valida e sanitiza parâmetros do FFmpeg"""
    sanitized = {}
    for key, value in params.items():
        if not re.match(r'^[a-zA-Z0-9_-]+$', key):
            raise ValueError(f"Chave inválida: {key}")
        sanitized[key] = quote(str(value))
    return sanitized

async def render_project(project_id: str, project: VideoProject):
    """
    Renderiza um projeto de vídeo.
    
    Args:
        project_id: ID do projeto
        project: Configuração do projeto
    """
    try:
        # Verificar se o ComfyUI está pronto
        if not comfy_server.is_ready():
            raise HTTPException(503, "Servidor de renderização não disponível")
            
        # Adquirir semáforo
        async with render_semaphore:
            # Configurar timeout
            try:
                async with asyncio.timeout(RENDER_TIMEOUT):
                    status = status_manager.get(project_id)
                    if not status:
                        return
                        
                    status.status = "rendering"
                    status.updated_at = datetime.now()
                    status_manager.set(project_id, status)
                    
                    # Criar clips para cada cena
                    clips = []
                    for i, scene in enumerate(project.scenes):
                        # Criar cena base
                        clip = await video_engine.create_scene(
                            width=project.width,
                            height=project.height,
                            duration=scene.duration,
                            fps=project.fps,
                            background=scene.background
                        )
                        
                        # Adicionar elementos
                        for element in scene.elements:
                            clip = await video_engine.add_element(
                                clip,
                                element.content,
                                element.start_time
                            )
                            
                        clips.append(clip)
                        
                        # Atualizar progresso
                        status.progress = (i + 1) / len(project.scenes) * 100
                        status.updated_at = datetime.now()
                        status_manager.set(project_id, status)
                        
                    # Aplicar transições entre cenas
                    final_clip = clips[0]
                    for i in range(1, len(clips)):
                        if project.scenes[i-1].transition:
                            final_clip = await video_engine.apply_transition(
                                final_clip,
                                clips[i],
                                project.scenes[i-1].transition
                            )
                        else:
                            final_clip = final_clip.append(clips[i])
                            
                    # Processar áudio se especificado
                    if project.audio:
                        try:
                            if project.audio["type"] == "file":
                                # Carregar arquivo de áudio
                                audio = await audio_engine.load_audio(
                                    project.audio["file"],
                                    start_time=0,
                                    end_time=final_clip.duration
                                )
                            elif project.audio["type"] == "tts":
                                # Gerar áudio via TTS
                                audio = await audio_engine.synthesize_speech(
                                    text=project.audio["text"],
                                    voice_id=project.audio.get("voice_id", "default"),
                                    language=project.audio.get("language", "pt-BR"),
                                    speed=project.audio.get("speed", 1.0),
                                    pitch=project.audio.get("pitch", 0.0),
                                    emotion=project.audio.get("emotion", "neutral")
                                )
                                
                            # Aplicar efeitos se especificados
                            if "effects" in project.audio:
                                audio = await audio_engine.apply_effects(
                                    audio,
                                    project.audio["effects"]
                                )
                                
                            # Exportar áudio temporário
                            temp_audio_path = f"output/temp_{project_id}_audio.wav"
                            await audio_engine.export_audio(
                                audio,
                                temp_audio_path,
                                format="wav",
                                bitrate="192k"
                            )
                            
                            # Atualizar parâmetros de renderização para incluir áudio
                            render_params = {}
                            render_params["audio"] = True
                            render_params["audio_file"] = temp_audio_path
                            
                        except Exception as e:
                            logger.error(f"Erro processando áudio: {e}")
                            status.error = f"Erro processando áudio: {e}"
                            status_manager.set(project_id, status)
                            # Continuar sem áudio
                            render_params["audio"] = False
                    
                    # Renderizar vídeo final
                    output_path = f"output/{project_id}.{project.output_format}"
                    os.makedirs("output", exist_ok=True)
                    
                    await video_engine.render_video(
                        final_clip,
                        output_path,
                        codec="libx264",
                        bitrate="8000k",
                        **render_params
                    )
                    
                    # Limpar arquivo de áudio temporário
                    if "temp_audio_path" in locals():
                        try:
                            os.remove(temp_audio_path)
                        except:
                            pass
                    
                    # Atualizar status
                    status.status = "completed"
                    status.output_url = f"/static/output/{project_id}.{project.output_format}"
                    status.progress = 100
                    status.updated_at = datetime.now()
                    status_manager.set(project_id, status)
                    
            except asyncio.TimeoutError:
                logger.error(f"Timeout renderizando projeto {project_id}")
                status = status_manager.get(project_id)
                if status:
                    status.status = "failed"
                    status.error = "Timeout durante renderização"
                    status.updated_at = datetime.now()
                    status_manager.set(project_id, status)
                    
    except Exception as e:
        logger.error(f"Erro renderizando projeto {project_id}: {e}")
        status = status_manager.get(project_id)
        if status:
            status.status = "failed"
            status.error = str(e)
            status.updated_at = datetime.now()
            status_manager.set(project_id, status)
    finally:
        # Limpar recursos
        try:
            for clip in clips:
                clip.close()
        except:
            pass 
