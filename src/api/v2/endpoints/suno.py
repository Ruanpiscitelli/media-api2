"""
Endpoints para integração com o Suno AI para geração de áudio e música.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import asyncio
import logging

from src.services.auth import get_current_user
from src.core.rate_limit import rate_limiter
from src.services.suno import SunoService
from src.core.gpu_manager import gpu_manager
from src.core.queue_manager import queue_manager

router = APIRouter(prefix="/v2/suno", tags=["suno"])
logger = logging.getLogger(__name__)
suno_service = SunoService()

class SunoGenerateRequest(BaseModel):
    """Modelo para requisição de geração de música"""
    prompt: str = Field(..., description="Prompt descritivo para geração")
    duration: int = Field(30, description="Duração desejada em segundos", ge=10, le=300)
    style: Optional[str] = Field(None, description="Estilo musical específico")
    tempo: Optional[int] = Field(None, description="BPM desejado", ge=40, le=200)
    key: Optional[str] = Field(None, description="Tom musical (ex: C, Am)")
    instruments: Optional[List[str]] = Field(None, description="Lista de instrumentos desejados")
    reference_audio: Optional[str] = Field(None, description="URL do áudio de referência")
    options: Optional[Dict] = Field(None, description="Opções avançadas de geração")

class SunoVoiceRequest(BaseModel):
    """Modelo para requisição de geração de voz cantada"""
    text: str = Field(..., description="Letra para cantar")
    melody: Optional[str] = Field(None, description="Melodia em formato MIDI ou MusicXML")
    voice_id: str = Field(..., description="ID da voz a ser usada")
    style: Optional[str] = Field(None, description="Estilo vocal")
    emotion: Optional[str] = Field("neutral", description="Emoção da voz")
    pitch_correction: Optional[bool] = Field(True, description="Aplicar correção de pitch")
    formant_shift: Optional[float] = Field(0.0, description="Ajuste de formantes (-1.0 a 1.0)")

class SunoResponse(BaseModel):
    """Modelo para resposta de geração"""
    task_id: str
    status: str
    estimated_time: int
    preview_url: Optional[str]

@router.post("/generate/music", response_model=SunoResponse)
async def generate_music(
    request: SunoGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """
    Gera música usando o Suno AI.
    Suporta geração condicional com referência e controle fino de parâmetros.
    """
    try:
        # Estimar recursos
        estimates = await suno_service.estimate_resources(request.duration)
        
        if estimates['vram_required'] > gpu_manager.get_available_vram():
            raise HTTPException(
                status_code=400,
                detail="Recursos GPU insuficientes. Tente uma duração menor."
            )
        
        # Iniciar geração
        task = await suno_service.start_music_generation(
            prompt=request.prompt,
            duration=request.duration,
            style=request.style,
            tempo=request.tempo,
            key=request.key,
            instruments=request.instruments,
            reference_audio=request.reference_audio,
            options=request.options,
            user_id=current_user.id
        )
        
        # Adicionar à fila de processamento
        background_tasks.add_task(
            suno_service.process_music_generation,
            task.task_id
        )
        
        return {
            "task_id": task.task_id,
            "status": "processing",
            "estimated_time": estimates['estimated_time'],
            "preview_url": task.preview_url
        }
        
    except Exception as e:
        logger.error(f"Erro na geração de música: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate/voice", response_model=SunoResponse)
async def generate_voice(
    request: SunoVoiceRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """
    Gera voz cantada usando o Suno AI.
    Suporta controle de melodia, estilo e emoção.
    """
    try:
        # Validar voz
        if not await suno_service.validate_voice(request.voice_id):
            raise HTTPException(
                status_code=400,
                detail="Voz não encontrada ou não suporta canto"
            )
        
        # Iniciar geração
        task = await suno_service.start_voice_generation(
            text=request.text,
            melody=request.melody,
            voice_id=request.voice_id,
            style=request.style,
            emotion=request.emotion,
            pitch_correction=request.pitch_correction,
            formant_shift=request.formant_shift,
            user_id=current_user.id
        )
        
        # Adicionar à fila
        background_tasks.add_task(
            suno_service.process_voice_generation,
            task.task_id
        )
        
        return {
            "task_id": task.task_id,
            "status": "processing",
            "estimated_time": 60,  # Tempo estimado em segundos
            "preview_url": task.preview_url
        }
        
    except Exception as e:
        logger.error(f"Erro na geração de voz: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """Obtém o status de uma tarefa de geração"""
    try:
        status = await suno_service.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada")
        return status
        
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/voices")
async def list_voices(
    style: Optional[str] = None,
    language: Optional[str] = None
):
    """Lista vozes disponíveis para canto"""
    try:
        voices = await suno_service.list_voices(
            style=style,
            language=language
        )
        return {"voices": voices}
        
    except Exception as e:
        logger.error(f"Erro ao listar vozes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/styles")
async def list_styles():
    """Lista estilos musicais suportados"""
    try:
        styles = await suno_service.list_styles()
        return {"styles": styles}
        
    except Exception as e:
        logger.error(f"Erro ao listar estilos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/instruments")
async def list_instruments():
    """Lista instrumentos suportados"""
    try:
        instruments = await suno_service.list_instruments()
        return {"instruments": instruments}
        
    except Exception as e:
        logger.error(f"Erro ao listar instrumentos: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 