"""
Validadores e checagens unificadas.
"""

import os
import re
import logging
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, status
from pydantic import BaseModel, validator, Field

from src.core.config import settings
from src.core.errors import ValidationError

logger = logging.getLogger(__name__)

# Modelos de Validação
class MediaRequest(BaseModel):
    """Modelo base para requisições de mídia"""
    model_type: str = Field(..., description="Tipo de modelo a usar")
    priority: int = Field(default=0, ge=0, le=3, description="Prioridade da tarefa")
    webhook_url: Optional[str] = Field(None, description="URL para callback")
    
    @validator("model_type")
    def validate_model_type(cls, v):
        valid_types = {"sdxl", "fish_speech", "video"}
        if v not in valid_types:
            raise ValueError(f"model_type deve ser um de: {valid_types}")
        return v
        
    @validator("webhook_url")
    def validate_webhook_url(cls, v):
        if v:
            pattern = r"^https?://[\w\-]+(\.[\w\-]+)+[/#?]?.*$"
            if not re.match(pattern, v):
                raise ValueError("webhook_url inválida")
        return v

class ImageRequest(MediaRequest):
    """Validação para geração de imagens"""
    prompt: str = Field(..., min_length=1, max_length=1000)
    negative_prompt: Optional[str] = Field(None, max_length=1000)
    width: int = Field(default=1024, ge=512, le=2048)
    height: int = Field(default=1024, ge=512, le=2048)
    num_inference_steps: int = Field(default=30, ge=10, le=100)
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0)
    
    @validator("prompt")
    def validate_prompt(cls, v):
        if len(v.split()) > 100:
            raise ValueError("prompt muito longo (max 100 palavras)")
        return v

class AudioRequest(MediaRequest):
    """Validação para geração de áudio"""
    text: str = Field(..., min_length=1, max_length=5000)
    voice_id: str = Field(..., regex=r"^[a-zA-Z0-9\-]+$")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch: float = Field(default=0.0, ge=-1.0, le=1.0)
    
    @validator("text")
    def validate_text(cls, v):
        if len(v.split()) > 1000:
            raise ValueError("texto muito longo (max 1000 palavras)")
        return v

class VideoRequest(MediaRequest):
    """Validação para geração de vídeos"""
    frames: List[str] = Field(..., min_items=2, max_items=50)
    fps: int = Field(default=30, ge=1, le=60)
    duration: float = Field(default=10.0, ge=1.0, le=300.0)
    
    @validator("frames")
    def validate_frames(cls, v):
        for frame in v:
            if not frame.startswith(("http://", "https://", "data:image/")):
                raise ValueError("frames devem ser URLs ou data URLs")
        return v

# Funções de Validação
async def validate_file_path(path: Union[str, Path]) -> Path:
    """
    Valida e normaliza caminho de arquivo.
    
    Args:
        path: Caminho a validar
        
    Returns:
        Path normalizado
        
    Raises:
        ValidationError: Se caminho inválido
    """
    try:
        path = Path(path).resolve()
        if not path.exists():
            raise ValidationError(
                message=f"Arquivo não encontrado: {path}",
                details={"path": str(path)}
            )
        return path
    except Exception as e:
        raise ValidationError(
            message=f"Caminho inválido: {e}",
            details={"path": str(path)}
        )

async def validate_media_file(
    file_path: Union[str, Path],
    allowed_types: Optional[List[str]] = None
) -> Path:
    """
    Valida arquivo de mídia.
    
    Args:
        file_path: Caminho do arquivo
        allowed_types: Extensões permitidas
        
    Returns:
        Path validado
        
    Raises:
        ValidationError: Se arquivo inválido
    """
    path = await validate_file_path(file_path)
    
    if allowed_types:
        if path.suffix.lower() not in allowed_types:
            raise ValidationError(
                message=f"Tipo de arquivo não permitido: {path.suffix}",
                details={
                    "path": str(path),
                    "allowed_types": allowed_types
                }
            )
            
    # Verifica tamanho
    try:
        size = path.stat().st_size
        if size > settings.max_file_size:
            raise ValidationError(
                message="Arquivo muito grande",
                details={
                    "path": str(path),
                    "size": size,
                    "max_size": settings.max_file_size
                }
            )
    except OSError as e:
        raise ValidationError(
            message=f"Erro ao verificar arquivo: {e}",
            details={"path": str(path)}
        )
        
    return path

async def validate_model_path(model_id: str) -> Path:
    """
    Valida caminho de modelo.
    
    Args:
        model_id: ID do modelo
        
    Returns:
        Path do modelo
        
    Raises:
        ValidationError: Se modelo inválido
    """
    try:
        if model_id == "sdxl":
            path = settings.models.sdxl_path
        elif model_id == "fish_speech":
            path = settings.models.fish_speech_path
        else:
            raise ValueError(f"Modelo desconhecido: {model_id}")
            
        if not path.exists():
            raise ValidationError(
                message=f"Modelo não encontrado: {model_id}",
                details={"model_id": model_id, "path": str(path)}
            )
            
        return path
        
    except Exception as e:
        raise ValidationError(
            message=f"Erro ao validar modelo: {e}",
            details={"model_id": model_id}
        )

# Funções de Checagem
async def check_system_resources() -> Dict[str, Any]:
    """
    Verifica recursos do sistema.
    
    Returns:
        Dict com status dos recursos
        
    Raises:
        ValidationError: Se recursos insuficientes
    """
    try:
        # Verifica espaço em disco
        disk = os.statvfs(settings.paths.workspace)
        free_space = disk.f_bavail * disk.f_frsize
        
        # Verifica memória
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                if ":" in line:
                    key, val = line.split(":")
                    mem[key.strip()] = int(val.split()[0])
                    
        # Verifica temperatura CPU
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            cpu_temp = int(f.read().strip()) / 1000
            
        status = {
            "disk_free": free_space,
            "mem_free": mem.get("MemAvailable", 0),
            "cpu_temp": cpu_temp,
            "timestamp": datetime.now().isoformat()
        }
        
        # Valida limites
        if free_space < settings.min_disk_space:
            raise ValidationError(
                message="Espaço em disco insuficiente",
                details=status
            )
            
        if mem.get("MemAvailable", 0) < settings.min_memory:
            raise ValidationError(
                message="Memória insuficiente",
                details=status
            )
            
        if cpu_temp > settings.max_cpu_temp:
            raise ValidationError(
                message="Temperatura CPU muito alta",
                details=status
            )
            
        return status
        
    except Exception as e:
        raise ValidationError(
            message=f"Erro ao verificar recursos: {e}",
            details={"error": str(e)}
        )

async def check_service_health() -> Dict[str, bool]:
    """
    Verifica saúde dos serviços.
    
    Returns:
        Dict com status dos serviços
        
    Raises:
        ValidationError: Se serviço crítico indisponível
    """
    from src.core.cache import cache
    
    status = {
        "redis": False,
        "gpu": False,
        "models": False
    }
    
    # Verifica Redis
    status["redis"] = await cache.health_check()
    
    # Verifica GPUs
    try:
        import torch
        status["gpu"] = torch.cuda.is_available()
    except:
        pass
        
    # Verifica modelos
    try:
        models = [
            settings.models.sdxl_path,
            settings.models.fish_speech_path
        ]
        status["models"] = all(path.exists() for path in models)
    except:
        pass
        
    # Valida serviços críticos
    if not status["gpu"]:
        raise ValidationError(
            message="GPUs indisponíveis",
            details=status
        )
        
    if not status["models"]:
        raise ValidationError(
            message="Modelos não encontrados",
            details=status
        )
        
    return status 