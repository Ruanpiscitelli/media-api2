"""
Endpoints para geração de thumbnails de imagens e vídeos.
"""

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import io
import os
import uuid
from PIL import Image
from src.core.auth import get_current_user
from src.core.rate_limit import rate_limiter
from src.services.thumbnails import thumbnail_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class ThumbnailRequest(BaseModel):
    """Modelo para requisição de geração de thumbnail"""
    width: int = Field(320, description="Largura do thumbnail")
    height: int = Field(180, description="Altura do thumbnail")
    timestamp: Optional[float] = Field(None, description="Momento do vídeo para capturar (em segundos)")
    quality: int = Field(85, description="Qualidade da imagem (1-100)")
    format: str = Field("JPEG", description="Formato de saída (JPEG, PNG, GIF)")
    smart_crop: bool = Field(True, description="Usar crop inteligente")

class ThumbnailResponse(BaseModel):
    """Modelo para resposta de geração de thumbnail"""
    status: str
    url: str
    metadata: Dict

@router.post("/generate")
async def generate_thumbnail(
    file: UploadFile = File(...),
    options: ThumbnailRequest = ThumbnailRequest(),
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """
    Gera thumbnail a partir de imagem ou vídeo
    """
    try:
        content_type = file.content_type
        file_content = await file.read()
        
        if content_type.startswith('video/'):
            # Salvar vídeo temporariamente
            temp_path = f"/tmp/{uuid.uuid4()}.mp4"
            with open(temp_path, 'wb') as f:
                f.write(file_content)
                
            try:
                # Usar serviço existente para vídeos
                thumbnail_path, _ = await thumbnail_service.get_or_generate(
                    video_path=temp_path,
                    animated=False,
                    timestamp=options.timestamp,
                    width=options.width,
                    quality=options.quality
                )
                
                return {
                    "status": "success",
                    "url": thumbnail_path,
                    "metadata": {
                        "type": "video",
                        "width": options.width,
                        "height": options.height,
                        "timestamp": options.timestamp
                    }
                }
                
            finally:
                os.remove(temp_path)
                
        elif content_type.startswith('image/'):
            try:
                with Image.open(io.BytesIO(file_content)) as img:
                    # Converter para RGB se necessário
                    if img.mode in ('RGBA', 'LA'):
                        img = img.convert('RGB')
                    
                    if options.smart_crop:
                        # Calcular proporções
                        target_ratio = options.width / options.height
                        img_ratio = img.width / img.height
                        
                        if img_ratio > target_ratio:
                            # Imagem muito larga - cortar laterais
                            new_width = int(img.height * target_ratio)
                            left = (img.width - new_width) // 2
                            img = img.crop((left, 0, left + new_width, img.height))
                        else:
                            # Imagem muito alta - cortar topo/base
                            new_height = int(img.width / target_ratio)
                            top = (img.height - new_height) // 2
                            img = img.crop((0, top, img.width, top + new_height))
                    
                    # Redimensionar
                    img = img.resize(
                        (options.width, options.height),
                        Image.LANCZOS
                    )
                    
                    # Salvar
                    output = io.BytesIO()
                    img.save(
                        output,
                        format=options.format,
                        quality=options.quality,
                        optimize=True
                    )
                    
                    # Salvar em disco
                    output_dir = "media/thumbnails"
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = f"{output_dir}/{uuid.uuid4()}.{options.format.lower()}"
                    
                    with open(output_path, 'wb') as f:
                        f.write(output.getvalue())
                    
                    return {
                        "status": "success",
                        "url": output_path,
                        "metadata": {
                            "type": "image",
                            "width": options.width,
                            "height": options.height,
                            "format": options.format,
                            "quality": options.quality
                        }
                    }
                    
            except Exception as e:
                logger.error(f"Erro processando imagem: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Erro processando imagem: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="Tipo de arquivo não suportado"
            )
            
    except Exception as e:
        logger.error(f"Erro gerando thumbnail: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/batch")
async def generate_batch_thumbnails(
    files: List[UploadFile] = File(...),
    options: ThumbnailRequest = ThumbnailRequest(),
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """
    Gera thumbnails para múltiplos arquivos
    """
    results = []
    
    for file in files:
        try:
            result = await generate_thumbnail(
                file=file,
                options=options,
                current_user=current_user,
                rate_limit=rate_limit
            )
            results.append({
                "filename": file.filename,
                "status": "success",
                "thumbnail": result
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e)
            })
            
    return {
        "status": "completed",
        "results": results
    } 