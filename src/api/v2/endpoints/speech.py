"""
Endpoints para síntese de voz, incluindo suporte a textos longos e streaming.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request, File, UploadFile, Query, Body, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, constr, HttpUrl, validator
from typing import List, Optional, Dict, Any
import re
from src.core.auth import get_current_user
from src.core.rate_limit import rate_limiter
from src.services.speech import SpeechService
from src.core.gpu_manager import gpu_manager
from src.core.queue_manager import queue_manager
import logging
from datetime import datetime

router = APIRouter(prefix="/synthesize/speech", tags=["Síntese de Voz"])
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
    """
    Modelo para requisição de síntese de voz.
    
    Attributes:
        text: Texto a ser sintetizado
        voice_id: ID da voz a ser usada
        emotion: Emoção desejada na fala
        speed: Velocidade da fala (0.5 a 2.0)
        pitch: Ajuste de tom (-20 a +20)
        volume: Volume da voz (0 a 2.0)
        language: Código do idioma (ex: pt-BR)
    """
    text: str = Field(..., min_length=1, max_length=1000, description="Texto a ser sintetizado")
    voice_id: str = Field(..., description="ID da voz a ser usada")
    emotion: str = Field("neutral", description="Emoção da fala")
    speed: float = Field(1.0, description="Velocidade", ge=0.5, le=2.0)
    pitch: int = Field(0, description="Ajuste de tom", ge=-20, le=20)
    volume: float = Field(1.0, description="Volume", ge=0, le=2.0)
    language: Optional[str] = Field(None, description="Código do idioma")

    @validator("text")
    def validate_text(cls, v):
        # Permitir caracteres Unicode incluindo acentos e pontuação comum
        v = re.sub(r'[^\p{L}\p{N}\s.,!?¡¿\-\'\"]+', '', v, flags=re.UNICODE)
        
        # Verificar comprimento após limpeza
        if len(v.strip()) < 1:
            raise ValueError("Texto vazio após limpeza")
            
        # Verificar tokens
        tokens = v.split()
        if len(tokens) > 200:
            raise ValueError("Texto muito longo (max 200 palavras)")
            
        return v.strip()

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

class VoiceCloneRequest(BaseModel):
    """
    Modelo para requisição de clonagem de voz.
    
    Attributes:
        name: Nome para identificar a voz
        description: Descrição da voz
        language: Idioma principal da voz
        gender: Gênero da voz (male/female)
    """
    name: str = Field(..., description="Nome da voz")
    description: Optional[str] = Field(None, description="Descrição")
    language: str = Field(..., description="Idioma principal")
    gender: str = Field(..., description="Gênero da voz")

class Voice(BaseModel):
    """
    Modelo para informações de uma voz.
    
    Attributes:
        id: Identificador único da voz
        name: Nome da voz
        language: Idioma da voz
        gender: Gênero da voz
        description: Descrição da voz
        preview_url: URL do áudio de preview
        created_at: Data de criação
    """
    id: str = Field(..., description="ID da voz")
    name: str = Field(..., description="Nome da voz")
    language: str = Field(..., description="Idioma")
    gender: str = Field(..., description="Gênero")
    description: Optional[str] = Field(None, description="Descrição")
    preview_url: Optional[HttpUrl] = Field(None, description="URL do preview")
    created_at: datetime = Field(..., description="Data de criação")

@router.post(
    "",
    summary="Sintetizar Voz",
    description="""
    Sintetiza voz a partir de texto usando Fish Speech.
    
    Features:
    - Múltiplas vozes em diferentes idiomas
    - Controle de emoção
    - Ajustes de velocidade e tom
    - Controle de volume
    """,
    responses={
        200: {
            "description": "Áudio gerado com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "id": "speech_123",
                        "url": "http://exemplo.com/audio/123.mp3",
                        "duration": 2.5,
                        "text": "Olá, como você está?"
                    }
                }
            }
        }
    }
)
async def synthesize_speech(
    request: SpeechRequest,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """Sintetiza voz a partir do texto fornecido."""
    try:
        result = await speech_service.synthesize(
            text=request.text,
            voice_id=request.voice_id,
            emotion=request.emotion,
            speed=request.speed,
            pitch=request.pitch,
            volume=request.volume,
            language=request.language,
            user_id=current_user.id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@router.get(
    "/voices",
    response_model=List[Voice],
    summary="Listar Vozes",
    description="Retorna lista de todas as vozes disponíveis.",
    responses={
        200: {
            "description": "Lista de vozes obtida com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "voices": [
                            {
                                "id": "pt_br_female",
                                "name": "Ana",
                                "language": "pt-BR",
                                "gender": "female"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def list_voices(
    language: Optional[str] = None,
    gender: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Lista todas as vozes disponíveis com filtros opcionais."""
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

@router.post(
    "/clone",
    response_model=Voice,
    summary="Clonar Voz",
    description="""
    Clona uma voz a partir de amostras de áudio.
    Requer pelo menos 3 amostras de áudio da voz a ser clonada.
    """,
    responses={
        200: {
            "description": "Voz clonada com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "id": "voice_123",
                        "name": "Minha Voz",
                        "language": "pt-BR",
                        "gender": "female",
                        "created_at": "2024-01-30T12:00:00Z"
                    }
                }
            }
        },
        400: {
            "description": "Dados inválidos ou amostras insuficientes"
        }
    }
)
async def clone_voice(
    name: str = Form(...),
    language: str = Form(...),
    gender: str = Form(...),
    description: Optional[str] = Form(None),
    samples: List[UploadFile] = File(..., description="Arquivos de áudio para clonagem"),
    current_user = Depends(get_current_user)
):
    """Clona uma voz a partir de amostras de áudio."""
    try:
        # Validação das amostras
        if len(samples) < 3:
            raise HTTPException(
                status_code=400,
                detail="São necessárias pelo menos 3 amostras de áudio"
            )

        voice = await speech_service.clone_voice(
            name=name,
            description=description,
            language=language,
            gender=gender,
            samples=samples,
            user_id=current_user.id
        )
        return voice
    except Exception as e:
        logger.error(f"Erro na clonagem de voz: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/voices/{voice_id}",
    response_model=Voice,
    summary="Detalhes da Voz",
    description="Retorna detalhes de uma voz específica.",
    responses={
        200: {
            "description": "Detalhes da voz obtidos com sucesso"
        },
        403: {
            "description": "Acesso negado - voz pertence a outro usuário"
        },
        404: {
            "description": "Voz não encontrada"
        }
    }
)
async def get_voice(
    voice_id: str,
    current_user = Depends(get_current_user)
):
    """Obtém detalhes de uma voz específica."""
    try:
        # Obtém a voz e verifica propriedade
        voice = await speech_service.get_voice(voice_id)
        if voice.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Você não tem permissão para acessar esta voz"
            )
        return voice
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=404, detail=str(e))

@router.delete(
    "/voices/{voice_id}",
    summary="Remover Voz",
    description="Remove uma voz clonada.",
    responses={
        200: {
            "description": "Voz removida com sucesso"
        },
        403: {
            "description": "Acesso negado - voz pertence a outro usuário"
        },
        404: {
            "description": "Voz não encontrada"
        }
    }
)
async def delete_voice(
    voice_id: str,
    current_user = Depends(get_current_user)
):
    """Remove uma voz clonada."""
    try:
        # Verifica se a voz existe e pertence ao usuário
        voice = await speech_service.get_voice(voice_id)
        if voice.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Você não tem permissão para remover esta voz"
            )
            
        await speech_service.delete_voice(
            voice_id=voice_id,
            user_id=current_user.id
        )
        return {"message": "Voz removida com sucesso"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=404, detail=str(e)) 