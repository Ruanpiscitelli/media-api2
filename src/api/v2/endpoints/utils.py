"""
Endpoints para utilitários e operações auxiliares.
"""

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from pydantic import BaseModel
from typing import Optional, Dict
from src.core.auth import get_current_user
from src.core.rate_limit import rate_limiter
from src.services.storage import StorageService
from src.services.optimization import OptimizationService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

storage_service = StorageService()
optimization_service = OptimizationService()

class StorageUsage(BaseModel):
    """Modelo para uso de armazenamento"""
    total_size: int
    file_count: int
    quota: int
    usage_percent: float

class OptimizationResult(BaseModel):
    """Modelo para resultado de otimização"""
    status: str
    optimized_url: str
    size_reduction: float
    original_size: int
    optimized_size: int

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    folder: Optional[str] = None,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """Upload de arquivo para o sistema"""
    try:
        result = await storage_service.upload_file(
            file=await file.read(),
            filename=file.filename,
            folder=folder,
            user_id=current_user.id
        )
        return {
            "status": "success",
            "file_url": result["url"]
        }
        
    except Exception as e:
        logger.error(f"Erro no upload do arquivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/storage/usage", response_model=StorageUsage)
async def storage_usage(
    current_user = Depends(get_current_user)
):
    """Retorna uso de armazenamento do usuário"""
    try:
        usage = await storage_service.get_usage(
            user_id=current_user.id
        )
        return {
            "total_size": usage["total_size"],
            "file_count": usage["file_count"],
            "quota": usage["quota"],
            "usage_percent": (usage["total_size"] / usage["quota"]) * 100
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter uso de armazenamento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize", response_model=OptimizationResult)
async def optimize_media(
    file: UploadFile = File(...),
    type: str,  # "image", "audio", "video"
    quality: int = 80,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """Otimiza um arquivo de mídia"""
    try:
        result = await optimization_service.optimize(
            file=await file.read(),
            file_type=type,
            quality=quality,
            user_id=current_user.id
        )
        return {
            "status": "success",
            "optimized_url": result["url"],
            "size_reduction": result["reduction"],
            "original_size": result["original_size"],
            "optimized_size": result["optimized_size"]
        }
        
    except Exception as e:
        logger.error(f"Erro na otimização do arquivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files")
async def list_files(
    folder: Optional[str] = None,
    type: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Lista arquivos do usuário"""
    try:
        files = await storage_service.list_files(
            user_id=current_user.id,
            folder=folder,
            file_type=type
        )
        return {"files": files}
        
    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user = Depends(get_current_user)
):
    """Remove um arquivo"""
    try:
        await storage_service.delete_file(
            file_id=file_id,
            user_id=current_user.id
        )
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Erro ao remover arquivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files/move")
async def move_file(
    file_id: str,
    destination: str,
    current_user = Depends(get_current_user)
):
    """Move um arquivo para outra pasta"""
    try:
        await storage_service.move_file(
            file_id=file_id,
            destination=destination,
            user_id=current_user.id
        )
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Erro ao mover arquivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files/copy")
async def copy_file(
    file_id: str,
    destination: str,
    current_user = Depends(get_current_user)
):
    """Copia um arquivo para outra pasta"""
    try:
        result = await storage_service.copy_file(
            file_id=file_id,
            destination=destination,
            user_id=current_user.id
        )
        return {
            "status": "success",
            "new_file_id": result["file_id"]
        }
        
    except Exception as e:
        logger.error(f"Erro ao copiar arquivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files/{file_id}/info")
async def file_info(
    file_id: str,
    current_user = Depends(get_current_user)
):
    """Obtém informações detalhadas de um arquivo"""
    try:
        info = await storage_service.get_file_info(
            file_id=file_id,
            user_id=current_user.id
        )
        return {"file": info}
        
    except Exception as e:
        logger.error(f"Erro ao obter informações do arquivo: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 