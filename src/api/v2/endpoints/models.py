"""
Endpoints para gerenciamento de modelos.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import os
from pathlib import Path

from src.core.config import settings
from src.services.auth import get_current_user
from src.services.model_manager import ModelManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["Models"])

# Schemas
class ModelInfo(BaseModel):
    """Informações de um modelo."""
    id: str = Field(..., description="ID do modelo")
    name: str = Field(..., description="Nome do modelo")
    type: str = Field(..., description="Tipo do modelo (SDXL, LoRA, etc)")
    version: str = Field(..., description="Versão do modelo")
    description: Optional[str] = Field(None, description="Descrição do modelo")
    size: int = Field(..., description="Tamanho em bytes")
    hash: str = Field(..., description="Hash do modelo")
    created_at: str = Field(..., description="Data de criação")
    updated_at: str = Field(..., description="Data da última atualização")
    status: str = Field(..., description="Status do modelo")
    metadata: dict = Field(default_factory=dict, description="Metadados adicionais")

class ModelList(BaseModel):
    """Lista de modelos."""
    models: List[ModelInfo] = Field(..., description="Lista de modelos")
    total: int = Field(..., description="Total de modelos")

# Endpoints
@router.get("", response_model=ModelList)
async def list_models(
    type: Optional[str] = None,
    status: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Lista modelos disponíveis.
    Permite filtrar por tipo e status.
    """
    try:
        model_manager = ModelManager()
        models = await model_manager.list_models(
            type=type,
            status=status
        )
        
        return {
            "models": models,
            "total": len(models)
        }
        
    except Exception as e:
        logger.error(f"Erro listando modelos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{model_id}", response_model=ModelInfo)
async def get_model(
    model_id: str,
    current_user = Depends(get_current_user)
):
    """
    Obtém informações detalhadas de um modelo específico.
    """
    try:
        model_manager = ModelManager()
        model = await model_manager.get_model(model_id)
        
        if not model:
            raise HTTPException(status_code=404, detail="Modelo não encontrado")
            
        return model
        
    except Exception as e:
        logger.error(f"Erro obtendo modelo {model_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_model(
    file: UploadFile = File(...),
    name: str = None,
    type: str = None,
    description: Optional[str] = None,
    metadata: Optional[dict] = None,
    current_user = Depends(get_current_user)
):
    """
    Faz upload de um novo modelo.
    """
    try:
        model_manager = ModelManager()
        
        # Upload do modelo
        model = await model_manager.upload_model(
            file=file,
            name=name or file.filename,
            type=type,
            description=description,
            metadata=metadata,
            uploaded_by=current_user.username
        )
        
        return {
            "status": "success",
            "model": model
        }
        
    except Exception as e:
        logger.error(f"Erro fazendo upload do modelo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{model_id}")
async def delete_model(
    model_id: str,
    current_user = Depends(get_current_user)
):
    """
    Remove um modelo.
    """
    try:
        model_manager = ModelManager()
        await model_manager.delete_model(model_id)
        
        return {
            "status": "success",
            "message": "Modelo removido com sucesso"
        }
        
    except Exception as e:
        logger.error(f"Erro removendo modelo {model_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{model_id}/download")
async def download_model(
    model_id: str,
    current_user = Depends(get_current_user)
):
    """
    Faz download de um modelo do hub.
    """
    try:
        model_manager = ModelManager()
        
        # Download do modelo
        model = await model_manager.download_model(
            model_id=model_id,
            requested_by=current_user.username
        )
        
        return {
            "status": "success",
            "model": model
        }
        
    except Exception as e:
        logger.error(f"Erro baixando modelo {model_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{model_id}/verify")
async def verify_model(
    model_id: str,
    current_user = Depends(get_current_user)
):
    """
    Verifica a integridade de um modelo.
    """
    try:
        model_manager = ModelManager()
        result = await model_manager.verify_model(model_id)
        
        return {
            "status": "success",
            "is_valid": result["is_valid"],
            "details": result["details"]
        }
        
    except Exception as e:
        logger.error(f"Erro verificando modelo {model_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 