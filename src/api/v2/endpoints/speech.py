"""
Endpoints para síntese de voz, incluindo suporte a textos longos e streaming.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, constr
from typing import List, Optional, Dict
import re
from src.core.auth import get_current_user
from src.core.rate_limit import rate_limiter
from src.services.speech import SpeechService
from src.core.gpu_manager import gpu_manager
from src.core.queue_manager import queue_manager
import logging

router = APIRouter(prefix="/synthesize/speech", tags=["speech"])
logger = logging.getLogger(__name__)
speech_service = SpeechService()

def sanitize_header_value(value: str) -> str:
    """
    Sanitiza valores de headers HTTP para prevenir header injection.
    Remove caracteres especiais e limita o tamanho.
    """
    if not value:
        return ""
    # Remove caracteres não permitidos em headers HTTP
    sanitized = re.sub(r'[^\w\-\.]', '', str(value))
    # Limita tamanho para prevenir ataques
    return sanitized[:64]

class SpeechRequest(BaseModel):
    """Modelo para requisição de síntese de voz"""
    text: str = Field(..., description="Texto para sintetizar")
    voice_id: constr(regex=r'^[a-zA-Z0-9\-\.]{1,64}$') = Field(..., description="ID da voz (apenas alfanuméricos, hífen e ponto)")
    emotion: str = Field("neutral", description="Emoção da voz")
    speed: float = Field(1.0, description="Velocidade da fala")
    pitch: float = Field(0.0, description="Tom da voz")
    volume: float = Field(1.0, description="Volume da voz")

class LongSpeechRequest(SpeechRequest):
    chunk_size: int = Field(400, description="Tamanho do chunk em caracteres")
    crossfade: float = Field(0.3, description="Duração do crossfade em segundos")
    webhook_url: str = Field(None, description="URL para notificação de progresso")

class StreamingSpeechRequest(SpeechRequest):
    chunk_size: int = Field(100, description="Tamanho do chunk em caracteres")

class SpeechResponse(BaseModel):
    """Modelo para resposta de síntese de voz"""
    status: str
    audio_path: str
    metadata: Dict

@router.post("/long", response_model=SpeechResponse)
async def generate_long_speech(
    request: LongSpeechRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """
    Gera áudio para textos longos.
    Divide o texto em chunks e processa em background.
    """
    try:
        # Estima recursos necessários
        estimates = await speech_service.estimate_resources(request.text)
        
        if estimates['vram_required'] > 24:  # Limite de 24GB VRAM
            raise HTTPException(
                status_code=400,
                detail="Texto muito longo. Divida em partes menores."
            )
            
        # Configura callback de progresso se webhook fornecido
        progress_callback = None
        if request.webhook_url:
            async def notify_progress(progress: Dict):
                # Implementar notificação via webhook
                pass
            progress_callback = notify_progress
            
        # Configurações para geração
        options = {
            'chunk_size': request.chunk_size,
            'crossfade': request.crossfade,
            'emotion': request.emotion,
            'speed': request.speed,
            'pitch': request.pitch,
            'volume': request.volume,
            'progress_callback': progress_callback
        }
        
        # Gera áudio em background
        result = await speech_service.generate_long_audio(
            text=request.text,
            voice_id=request.voice_id,
            options=options
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro gerando áudio: {str(e)}"
        )

@router.post("/stream")
async def stream_speech(
    request: StreamingSpeechRequest,
    current_user = Depends(get_current_user)
):
    """
    Gera áudio em tempo real usando streaming.
    Retorna chunks de áudio conforme são gerados.
    """
    try:
        # Função geradora para streaming
        async def generate():
            async for chunk in speech_service.stream_speech(
                text=request.text,
                voice_id=request.voice_id,
                chunk_size=request.chunk_size
            ):
                yield chunk
                
        # Sanitiza valores dos headers
        safe_voice_id = sanitize_header_value(request.voice_id)
        safe_chunk_size = sanitize_header_value(str(request.chunk_size))
                
        # Retorna resposta em streaming com headers sanitizados
        return StreamingResponse(
            generate(),
            media_type="audio/wav",
            headers={
                "X-Voice-ID": safe_voice_id,
                "X-Chunk-Size": safe_chunk_size
            }
        )
        
    except Exception as e:
        logger.error(f"Erro no streaming de áudio: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro no streaming: {str(e)}"
        )

@router.get("/estimate")
async def estimate_generation(
    text: str,
    current_user = Depends(get_current_user)
):
    """
    Estima recursos necessários para gerar o áudio.
    """
    try:
        return await speech_service.estimate_resources(text)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na estimativa: {str(e)}"
        )

@router.get("/voices")
async def list_voices(
    language: Optional[str] = None,
    gender: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Lista vozes disponíveis"""
    try:
        voices = await speech_service.list_voices(
            language=language,
            gender=gender
        )
        return {"voices": voices}
        
    except Exception as e:
        logger.error(f"Erro ao listar vozes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch", response_model=List[SpeechResponse])
async def synthesize_batch(
    requests: List[SpeechRequest],
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """Sintetiza múltiplos textos em batch"""
    try:
        results = []
        for request in requests:
            result = await speech_service.synthesize_batch(
                request.dict(),
                user_id=current_user.id
            )
            results.append(result)
            
        return results
        
    except Exception as e:
        logger.error(f"Erro na síntese em batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/languages")
async def list_languages(
    current_user = Depends(get_current_user)
):
    """Lista idiomas suportados"""
    try:
        languages = await speech_service.list_languages()
        return {"languages": languages}
        
    except Exception as e:
        logger.error(f"Erro ao listar idiomas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/emotions")
async def list_emotions(
    current_user = Depends(get_current_user)
):
    """Lista emoções disponíveis"""
    try:
        emotions = await speech_service.list_emotions()
        return {"emotions": emotions}
        
    except Exception as e:
        logger.error(f"Erro ao listar emoções: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clone")
async def clone_voice(
    name: str,
    samples: List[str],
    language: str = "pt-BR",
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """Clona uma voz a partir de amostras de áudio"""
    try:
        result = await speech_service.clone_voice(
            name=name,
            samples=samples,
            language=language,
            user_id=current_user.id
        )
        return {
            "status": "success",
            "voice_id": result["voice_id"]
        }
        
    except Exception as e:
        logger.error(f"Erro na clonagem de voz: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 