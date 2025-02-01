"""
Endpoints para geração e manipulação de imagens.
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
import os
from pathlib import Path
from uuid import uuid4

router = APIRouter(tags=["images"])
logger = logging.getLogger(__name__)
image_service = ImageService()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

async def save_upload_file(upload_file: UploadFile) -> Path:
    """
    Salva um arquivo enviado e retorna o caminho
    """
    # Gera nome único para evitar conflitos
    file_id = uuid4()
    extension = Path(upload_file.filename).suffix
    file_path = UPLOAD_DIR / f"{file_id}{extension}"
    
    # Salva o arquivo
    content = await upload_file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    return file_path

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
    current_user: Dict = Depends(get_current_user),
    rate_limit: Dict = Depends(rate_limiter)
) -> Dict:
    """
    Gera uma imagem usando SDXL de forma assíncrona com gerenciamento de recursos.
    
    Args:
        request: Parâmetros da geração de imagem
        background_tasks: Gerenciador de tarefas em background
        current_user: Usuário autenticado
        rate_limit: Limitador de taxa de requisições
    
    Returns:
        Dict com status da tarefa e ID para acompanhamento
    """
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
            user_id=current_user["id"],
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
            ),
            "images": [],
            "metadata": {
                "gpu_id": gpu.id,
                "queue_position": await queue_manager.get_position(task_id)
            }
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
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """
    Aumenta a resolução de uma imagem.
    """
    try:
        # Salva o arquivo enviado
        image_path = await save_upload_file(image)
        
        # Processa a imagem
        result = await image_service.upscale(
            image_path=str(image_path),
            scale=scale
        )
        
        # Remove o arquivo temporário
        os.unlink(image_path)
        
        return result
        
    except Exception as e:
        logger.error(f"Erro no upscale: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process")
async def process_image(
    operations: List[Dict],
    image: UploadFile = File(...),
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    """
    Aplica operações em uma imagem.
    """
    try:
        # Salva o arquivo enviado
        image_path = await save_upload_file(image)
        
        # Processa a imagem
        result = await image_service.process_image(
            image_path=str(image_path),
            operations=operations
        )
        
        # Remove o arquivo temporário
        os.unlink(image_path)
        
        return result
        
    except Exception as e:
        logger.error(f"Erro no processamento: {e}")
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