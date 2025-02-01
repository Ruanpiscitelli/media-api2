"""
Endpoints para integração com Fish Speech.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.core.config import settings
from src.services.auth import get_current_user
from src.services.fish_speech import fish_speech_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fish-speech", tags=["Fish Speech"])

# Schemas
class Voice(BaseModel):
    """Informações de uma voz."""
    id: str = Field(..., description="ID da voz")
    name: str = Field(..., description="Nome da voz")
    language: str = Field(..., description="Idioma da voz")
    gender: str = Field(..., description="Gênero da voz")
    preview_url: Optional[str] = Field(None, description="URL do áudio de preview")
    description: Optional[str] = Field(None, description="Descrição da voz")

class VoiceList(BaseModel):
    """Lista de vozes disponíveis."""
    voices: List[Voice] = Field(..., description="Lista de vozes")
    total: int = Field(..., description="Total de vozes")

# Endpoints
@router.get("/voices", response_model=VoiceList)
async def list_voices(
    language: Optional[str] = None,
    gender: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Lista vozes disponíveis no Fish Speech.
    Permite filtrar por idioma e gênero.
    """
    try:
        voices = await fish_speech_client.list_voices(
            language=language,
            gender=gender
        )
        
        return {
            "voices": voices,
            "total": len(voices)
        }
        
    except Exception as e:
        logger.error(f"Erro listando vozes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/voices/{voice_id}", response_model=Voice)
async def get_voice(
    voice_id: str,
    current_user = Depends(get_current_user)
):
    """
    Obtém informações detalhadas de uma voz específica.
    """
    try:
        voice = await fish_speech_client.get_voice(voice_id)
        if not voice:
            raise HTTPException(status_code=404, detail="Voz não encontrada")
            
        return voice
        
    except Exception as e:
        logger.error(f"Erro obtendo voz {voice_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/preview/{voice_id}")
async def generate_preview(
    voice_id: str,
    text: str,
    current_user = Depends(get_current_user)
):
    """
    Gera um áudio de preview com uma voz específica.
    """
    try:
        result = await fish_speech_client.generate_preview(
            voice_id=voice_id,
            text=text
        )
        
        return {
            "status": "success",
            "audio_url": result["url"],
            "duration": result["duration"]
        }
        
    except Exception as e:
        logger.error(f"Erro gerando preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/languages")
async def list_languages(
    current_user = Depends(get_current_user)
):
    """
    Lista idiomas suportados pelo Fish Speech.
    """
    try:
        languages = await fish_speech_client.list_languages()
        
        return {
            "languages": languages,
            "total": len(languages)
        }
        
    except Exception as e:
        logger.error(f"Erro listando idiomas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/emotions")
async def list_emotions(
    current_user = Depends(get_current_user)
):
    """
    Lista emoções suportadas pelo Fish Speech.
    """
    try:
        emotions = await fish_speech_client.list_emotions()
        
        return {
            "emotions": emotions,
            "total": len(emotions)
        }
        
    except Exception as e:
        logger.error(f"Erro listando emoções: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 