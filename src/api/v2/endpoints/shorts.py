"""
Endpoints para geração de YouTube Shorts usando IA.
Integra com Suno AI para música e voz, e FastHuayuan para vídeo.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import asyncio
import logging
import json
import uuid
from pathlib import Path

from src.core.auth import get_current_user
from src.core.rate_limit import rate_limiter
from src.services.shorts import ShortsService
from src.core.gpu_manager import gpu_manager
from src.core.queue_manager import queue_manager

router = APIRouter(prefix="/v2/shorts", tags=["shorts"])
logger = logging.getLogger(__name__)
shorts_service = ShortsService()

class ShortRequest(BaseModel):
    """Modelo para requisição de geração de short"""
    title: str = Field(..., description="Título do vídeo")
    description: str = Field(..., description="Descrição para gerar o vídeo")
    duration: int = Field(60, description="Duração em segundos", ge=15, le=60)
    style: str = Field("cinematic", description="Estilo visual")
    music_prompt: Optional[str] = Field(None, description="Prompt para música de fundo")
    voice_id: Optional[str] = Field(None, description="ID da voz para narração")
    hashtags: Optional[List[str]] = Field(None, description="Hashtags para o vídeo")
    watermark: Optional[str] = Field(None, description="Texto da marca d'água")
    options: Optional[Dict] = Field(None, description="Opções avançadas")

class ShortResponse(BaseModel):
    """Modelo para resposta de geração"""
    task_id: str
    status: str
    estimated_time: int
    preview_url: Optional[str]

@router.post("/generate", response_model=ShortResponse)
async def generate_short(
    request: ShortRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """
    Gera um YouTube Short usando IA.
    Integra geração de vídeo, música e voz.
    """
    try:
        # Estimar recursos
        estimates = await shorts_service.estimate_resources(request.duration)
        
        if estimates['vram_required'] > gpu_manager.get_available_vram():
            raise HTTPException(
                status_code=400,
                detail="Recursos GPU insuficientes. Tente uma duração menor."
            )
        
        # Iniciar geração
        task = await shorts_service.start_generation(
            title=request.title,
            description=request.description,
            duration=request.duration,
            style=request.style,
            music_prompt=request.music_prompt,
            voice_id=request.voice_id,
            hashtags=request.hashtags,
            watermark=request.watermark,
            options=request.options,
            user_id=current_user.id
        )
        
        # Adicionar à fila de processamento
        background_tasks.add_task(
            shorts_service.process_generation,
            task.task_id
        )
        
        return {
            "task_id": task.task_id,
            "status": "processing",
            "estimated_time": estimates['estimated_time'],
            "preview_url": task.preview_url
        }
        
    except Exception as e:
        logger.error(f"Erro na geração de short: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """Obtém o status de uma tarefa de geração"""
    try:
        status = await shorts_service.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada")
        return status
        
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """
    Faz upload de um vídeo para usar como base do short.
    Suporta mp4, mov e avi.
    """
    try:
        # Validar arquivo
        if not file.content_type.startswith('video/'):
            raise HTTPException(
                status_code=400,
                detail="Arquivo deve ser um vídeo"
            )
            
        # Salvar arquivo
        video_path = await shorts_service.save_uploaded_video(
            file,
            user_id=current_user.id
        )
        
        return {
            "status": "success",
            "video_path": video_path
        }
        
    except Exception as e:
        logger.error(f"Erro no upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates")
async def list_templates():
    """Lista templates disponíveis para shorts"""
    try:
        templates = await shorts_service.list_templates()
        return {"templates": templates}
        
    except Exception as e:
        logger.error(f"Erro listando templates: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 