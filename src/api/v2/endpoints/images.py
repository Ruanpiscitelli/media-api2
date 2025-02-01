"""
Endpoints para geração de imagens usando SDXL.
"""

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict
from src.core.auth import get_current_user
from src.core.rate_limit import rate_limiter
from src.services.image import ImageService
from src.core.gpu_manager import gpu_manager
from src.core.queue_manager import queue_manager
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
image_service = ImageService()

class ImageGenerationRequest(BaseModel):
    """Modelo para requisição de geração de imagem"""
    prompt: str
    negative_prompt: Optional[str] = ""
    width: int = 1024
    height: int = 1024
    steps: int = 30
    cfg_scale: float = 7.0
    batch_size: int = 1
    style: Optional[str] = None
    loras: Optional[List[Dict[str, float]]] = None

class ImageResponse(BaseModel):
    """Modelo para resposta de geração de imagem"""
    status: str
    images: List[str]
    metadata: Dict

@router.post("/generate", response_model=ImageResponse)
async def generate_image(
    request: ImageGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """Gera uma imagem usando SDXL"""
    try:
        # Verifica disponibilidade de GPU
        gpu = await gpu_manager.get_available_gpu(
            min_vram=8000  # Requer 8GB VRAM para SDXL
        )
        if not gpu:
            raise HTTPException(
                status_code=503,
                detail="Nenhuma GPU com VRAM suficiente disponível"
            )
        
        # Cria tarefa na fila
        task_id = await queue_manager.enqueue_task(
            task_type="image_generation",
            params=request.dict(),
            gpu_id=gpu.id,
            priority=1
        )
        
        # Inicia processamento em background
        background_tasks.add_task(
            gpu_manager.process_task,
            task_id=task_id,
            gpu_id=gpu.id
        )
        
        return {
            "status": "processing",
            "task_id": task_id,
            "estimated_time": await gpu_manager.estimate_completion_time(
                gpu.id,
                task_type="image"
            )
        }
        
    except Exception as e:
        logger.error(f"Erro na geração de imagem: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch", response_model=List[ImageResponse])
async def generate_batch(
    requests: List[ImageGenerationRequest],
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """Gera múltiplas imagens em batch"""
    try:
        results = []
        for request in requests:
            result = await image_service.generate_batch(
                request.dict(),
                user_id=current_user.id
            )
            results.append(result)
            
        return results
        
    except Exception as e:
        logger.error(f"Erro na geração em batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upscale")
async def upscale_image(
    image: UploadFile = File(...),
    scale: int = 2,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """Aumenta a resolução de uma imagem"""
    try:
        result = await image_service.upscale(
            image=await image.read(),
            scale=scale,
            user_id=current_user.id
        )
        return {
            "status": "success",
            "image": result["image_url"]
        }
        
    except Exception as e:
        logger.error(f"Erro no upscale: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/styles")
async def list_styles(
    current_user = Depends(get_current_user)
):
    """Lista estilos disponíveis"""
    try:
        styles = await image_service.list_styles()
        return {"styles": styles}
        
    except Exception as e:
        logger.error(f"Erro ao listar estilos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/loras")
async def list_loras(
    current_user = Depends(get_current_user)
):
    """Lista LoRAs disponíveis"""
    try:
        loras = await image_service.list_loras()
        return {"loras": loras}
        
    except Exception as e:
        logger.error(f"Erro ao listar LoRAs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/enhance")
async def enhance_image(
    enhancement_type: str,
    image: UploadFile = File(...),
    strength: float = 1.0,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """Melhora uma imagem (redução de ruído, aumento de nitidez, etc)"""
    try:
        result = await image_service.enhance(
            image=await image.read(),
            enhancement_type=enhancement_type,
            strength=strength,
            user_id=current_user.id
        )
        return {
            "status": "success",
            "image": result["image_url"]
        }
        
    except Exception as e:
        logger.error(f"Erro no enhancement: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 