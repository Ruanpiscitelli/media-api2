"""
Endpoints para gerenciamento e clonagem de vozes.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from typing import List, Optional, Dict
import shutil
import os
from pydantic import BaseModel
from datetime import datetime

from src.core.voice import VoiceManager, VoiceCloner
from src.models.voice import Voice, VoiceCloneRequest, VoiceCloneStatus
from src.utils.storage import save_uploaded_file
from src.utils.validators import validate_audio_file

router = APIRouter(prefix="/v2/voices", tags=["voices"])

# Schemas
class VoiceResponse(BaseModel):
    id: str
    name: str
    language: str
    gender: str
    description: str
    tags: List[str]
    preview_url: str
    capabilities: Dict
    samples: List[Dict]

class VoiceListResponse(BaseModel):
    voices: List[VoiceResponse]

# Instâncias dos gerenciadores
voice_manager = VoiceManager()
voice_cloner = VoiceCloner()

@router.get("/list", response_model=VoiceListResponse)
async def list_voices():
    """Lista todas as vozes disponíveis no sistema."""
    voices = await voice_manager.list_voices()
    return {"voices": voices}

@router.get("/{voice_id}", response_model=VoiceResponse)
async def get_voice(voice_id: str):
    """Obtém detalhes de uma voz específica."""
    voice = await voice_manager.get_voice(voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail="Voz não encontrada")
    return voice

@router.post("/clone")
async def clone_voice(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    description: str = Form(...),
    language: str = Form(...),
    gender: str = Form(...),
    samples: List[UploadFile] = File(...),
    transcriptions: List[str] = Form(...),
    settings: Dict = Form(...)
):
    """Inicia o processo de clonagem de voz."""
    
    # Validar arquivos de áudio
    for sample in samples:
        if not validate_audio_file(sample):
            raise HTTPException(
                status_code=400, 
                detail=f"Arquivo inválido: {sample.filename}"
            )

    # Salvar arquivos temporariamente
    sample_paths = []
    for sample in samples:
        path = await save_uploaded_file(sample, "temp/voice_samples")
        sample_paths.append(path)

    # Criar requisição de clonagem
    clone_request = VoiceCloneRequest(
        name=name,
        description=description,
        language=language,
        gender=gender,
        sample_paths=sample_paths,
        transcriptions=transcriptions,
        settings=settings
    )

    # Iniciar processo de clonagem em background
    clone_id = await voice_cloner.start_cloning(clone_request)
    background_tasks.add_task(voice_cloner.process_cloning, clone_id)

    return {
        "clone_id": clone_id,
        "status": "processing",
        "estimated_time": 300,
        "progress": 0
    }

@router.get("/clone/{clone_id}/status")
async def get_clone_status(clone_id: str):
    """Verifica o status de um processo de clonagem."""
    status = await voice_cloner.get_status(clone_id)
    if not status:
        raise HTTPException(status_code=404, detail="Processo de clonagem não encontrado")
    return status

@router.post("/add")
async def add_voice(
    name: str = Form(...),
    description: str = Form(...),
    language: str = Form(...),
    gender: str = Form(...),
    model_file: UploadFile = File(...),
    config_file: UploadFile = File(...),
    preview_audio: UploadFile = File(...),
    tags: List[str] = Form(...)
):
    """Adiciona uma nova voz ao sistema."""
    
    # Validar arquivos
    if not model_file.filename.endswith('.pth'):
        raise HTTPException(status_code=400, detail="Arquivo de modelo inválido")
    
    if not config_file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Arquivo de configuração inválido")
    
    if not validate_audio_file(preview_audio):
        raise HTTPException(status_code=400, detail="Arquivo de preview inválido")

    # Salvar arquivos
    model_path = await save_uploaded_file(model_file, "models/voices")
    config_path = await save_uploaded_file(config_file, "models/voices")
    preview_path = await save_uploaded_file(preview_audio, "media/voice_previews")

    # Criar voz
    voice = Voice(
        name=name,
        description=description,
        language=language,
        gender=gender,
        model_path=model_path,
        config_path=config_path,
        preview_url=preview_path,
        tags=tags
    )

    voice_id = await voice_manager.add_voice(voice)
    return {"voice_id": voice_id}

@router.put("/{voice_id}")
async def update_voice(
    voice_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None
):
    """Atualiza uma voz existente."""
    voice = await voice_manager.get_voice(voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail="Voz não encontrada")

    updates = {}
    if name:
        updates["name"] = name
    if description:
        updates["description"] = description
    if tags:
        updates["tags"] = tags

    updated_voice = await voice_manager.update_voice(voice_id, updates)
    return updated_voice

@router.delete("/{voice_id}")
async def delete_voice(voice_id: str):
    """Remove uma voz do sistema."""
    voice = await voice_manager.get_voice(voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail="Voz não encontrada")

    await voice_manager.delete_voice(voice_id)
    return {"message": "Voz removida com sucesso"}

@router.post("/clone/zero-shot")
async def clone_voice_zero_shot(
    reference_voice: str,
    target_characteristics: Dict,
    background_tasks: BackgroundTasks
):
    """Clonagem de voz sem amostras (zero-shot)."""
    
    # Validar voz de referência
    reference = await voice_manager.get_voice(reference_voice)
    if not reference:
        raise HTTPException(status_code=404, detail="Voz de referência não encontrada")
    
    # Criar requisição de clonagem
    clone_request = VoiceCloneRequest(
        name=f"Zero-Shot Clone of {reference.name}",
        description="Clonagem zero-shot",
        language=reference.language,
        gender=target_characteristics.get("gender", reference.gender),
        settings={
            "zero_shot": True,
            "target_characteristics": target_characteristics
        }
    )
    
    # Iniciar processo
    clone_id = await voice_cloner.start_cloning(clone_request)
    background_tasks.add_task(voice_cloner.process_cloning, clone_id)
    
    return {
        "clone_id": clone_id,
        "status": "processing",
        "estimated_time": 60
    }

@router.post("/clone/few-shot")
async def clone_voice_few_shot(
    base_voice: str = Form(...),
    samples: List[UploadFile] = File(...),
    transcriptions: List[str] = Form(...),
    adaptation_config: Dict = Form(...),
    background_tasks: BackgroundTasks
):
    """Clonagem de voz com poucas amostras (few-shot)."""
    
    # Validar voz base
    base = await voice_manager.get_voice(base_voice)
    if not base:
        raise HTTPException(status_code=404, detail="Voz base não encontrada")
    
    # Validar arquivos
    for sample in samples:
        if not validate_audio_file(sample):
            raise HTTPException(
                status_code=400,
                detail=f"Arquivo inválido: {sample.filename}"
            )
    
    # Salvar amostras
    sample_paths = []
    for sample in samples:
        path = await save_uploaded_file(sample, "temp/voice_samples")
        sample_paths.append(path)
    
    # Criar requisição
    clone_request = VoiceCloneRequest(
        name=f"Few-Shot Adaptation of {base.name}",
        description="Adaptação few-shot",
        language=base.language,
        gender=base.gender,
        sample_paths=sample_paths,
        transcriptions=transcriptions,
        settings={
            "few_shot": True,
            "base_voice": base_voice,
            **adaptation_config
        }
    )
    
    # Iniciar processo
    clone_id = await voice_cloner.start_cloning(clone_request)
    background_tasks.add_task(voice_cloner.process_cloning, clone_id)
    
    return {
        "clone_id": clone_id,
        "status": "processing",
        "estimated_time": 120
    }

@router.get("/{voice_id}/metrics")
async def get_voice_metrics(voice_id: str):
    """Obtém métricas de qualidade e performance de uma voz."""
    
    voice = await voice_manager.get_voice(voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail="Voz não encontrada")
    
    # Coletar métricas
    metrics = await voice_manager.get_metrics(voice_id)
    
    return {
        "voice_id": voice_id,
        "metrics": {
            "mos": metrics.get("mos", 0),
            "pesq": metrics.get("pesq", 0),
            "stoi": metrics.get("stoi", 0),
            "character_error_rate": metrics.get("cer", 0),
            "word_error_rate": metrics.get("wer", 0),
            "real_time_factor": metrics.get("rtf", 0)
        },
        "performance": {
            "average_generation_time": metrics.get("avg_time", 0),
            "gpu_utilization": metrics.get("gpu_util", 0),
            "memory_usage": metrics.get("memory", "0GB")
        }
    }

@router.post("/synthesize/multilingual")
async def synthesize_multilingual(
    text: str,
    voice_id: str,
    target_language: str,
    translation_config: Optional[Dict] = None,
    preserve_accent: bool = True
):
    """Sintetiza voz com suporte multilíngue."""
    
    voice = await voice_manager.get_voice(voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail="Voz não encontrada")
    
    # Validar idioma
    if target_language not in voice_manager.supported_languages:
        raise HTTPException(status_code=400, detail="Idioma não suportado")
    
    # Configurar tradução
    if translation_config and translation_config.get("enabled"):
        text = await voice_manager.translate_text(
            text,
            target_language,
            preserve_emphasis=translation_config.get("preserve_emphasis", True)
        )
    
    # Gerar áudio
    result = await voice_manager.generate_speech(
        text=text,
        voice_id=voice_id,
        target_language=target_language,
        preserve_accent=preserve_accent
    )
    
    return result 