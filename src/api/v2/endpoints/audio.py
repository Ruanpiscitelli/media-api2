"""
Endpoints para processamento e geração de áudio.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import os
from pathlib import Path

from src.core.config import settings
from src.services.auth import get_current_user
from src.services.fish_speech import fish_speech_client
from src.utils.audio import AudioProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audio", tags=["Audio"])

# Schemas
class AudioGenerationRequest(BaseModel):
    """Request para geração de áudio."""
    text: str = Field(..., description="Texto para sintetizar")
    voice_id: str = Field(..., description="ID da voz a ser usada")
    language: str = Field(default="pt-BR", description="Idioma do texto")
    speed: float = Field(default=1.0, description="Velocidade da fala (0.5 a 2.0)")
    pitch: float = Field(default=0.0, description="Ajuste de pitch (-10 a 10)")
    emotion: Optional[str] = Field(default=None, description="Emoção da fala")

class AudioProcessingRequest(BaseModel):
    """Request para processamento de áudio."""
    operations: List[dict] = Field(..., description="Lista de operações a serem aplicadas")
    output_format: str = Field(default="mp3", description="Formato de saída")
    quality: str = Field(default="high", description="Qualidade do áudio")

# Endpoints
@router.post("/generate", response_model=dict)
async def generate_audio(
    request: AudioGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """
    Gera áudio a partir de texto usando Fish Speech.
    """
    try:
        # Gerar áudio
        result = await fish_speech_client.generate_speech(
            text=request.text,
            voice_id=request.voice_id,
            language=request.language,
            speed=request.speed,
            pitch=request.pitch,
            emotion=request.emotion
        )
        
        return {
            "status": "success",
            "audio_url": result["url"],
            "duration": result["duration"],
            "text": request.text
        }
        
    except Exception as e:
        logger.error(f"Erro gerando áudio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process")
async def process_audio(
    request: AudioProcessingRequest,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """
    Processa um arquivo de áudio aplicando operações.
    """
    try:
        processor = AudioProcessor()
        
        # Processar áudio
        result = await processor.process_audio(
            input_file=file,
            operations=request.operations,
            output_format=request.output_format,
            quality=request.quality
        )
        
        return {
            "status": "success",
            "audio_url": result["url"],
            "duration": result["duration"]
        }
        
    except Exception as e:
        logger.error(f"Erro processando áudio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/merge")
async def merge_audio(
    files: List[UploadFile] = File(...),
    current_user = Depends(get_current_user)
):
    """
    Combina múltiplos arquivos de áudio em um único arquivo.
    """
    try:
        processor = AudioProcessor()
        
        # Mesclar áudios
        result = await processor.merge_audio_files(files)
        
        return {
            "status": "success",
            "audio_url": result["url"],
            "duration": result["duration"]
        }
        
    except Exception as e:
        logger.error(f"Erro mesclando áudios: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract")
async def extract_audio(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """
    Extrai áudio de um arquivo de vídeo.
    """
    try:
        processor = AudioProcessor()
        
        # Extrair áudio
        result = await processor.extract_audio_from_video(file)
        
        return {
            "status": "success",
            "audio_url": result["url"],
            "duration": result["duration"]
        }
        
    except Exception as e:
        logger.error(f"Erro extraindo áudio: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 