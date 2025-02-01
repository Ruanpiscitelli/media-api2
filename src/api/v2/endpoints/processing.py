"""
Endpoints para processamento de imagem e texto.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from PIL import Image
import io

from src.core.text_engine import text_engine
from src.core.image_engine import image_engine

router = APIRouter(prefix="/v2/processing", tags=["processing"])

# Schemas
class TextProcessingRequest(BaseModel):
    """Requisição para processamento de texto."""
    text: str
    font_name: str
    size: float
    max_width: Optional[int] = None
    language: Optional[str] = None
    color: tuple[int, int, int] = (0, 0, 0)
    alignment: str = "left"

class ImageOperation(BaseModel):
    """Operação de processamento de imagem."""
    type: str
    params: dict = {}

class ImageProcessingRequest(BaseModel):
    """Requisição para processamento de imagem."""
    operations: List[ImageOperation]
    output_format: str = "PIL"

# Endpoints
@router.post("/text")
async def process_text(request: TextProcessingRequest):
    """
    Processa texto com suporte a múltiplos idiomas e fontes.
    
    Args:
        request: Parâmetros do processamento de texto
        
    Returns:
        Resultado do processamento incluindo imagem e métricas
    """
    try:
        result = text_engine.process_text(
            text=request.text,
            font_name=request.font_name,
            size=request.size,
            max_width=request.max_width,
            language=request.language,
            color=request.color,
            alignment=request.alignment
        )
        
        # Converter imagem PIL para bytes
        img_byte_arr = io.BytesIO()
        result["image"].save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()
        
        # Substituir imagem PIL por bytes
        result["image"] = img_byte_arr
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/image")
async def process_image(
    file: UploadFile = File(...),
    request: ImageProcessingRequest = None,
    background_tasks: BackgroundTasks = None
):
    """
    Processa imagem aplicando operações especificadas.
    
    Args:
        file: Arquivo de imagem
        request: Parâmetros do processamento
        background_tasks: Tarefas em background
        
    Returns:
        Imagem processada em formato especificado
    """
    try:
        # Ler imagem
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Processar imagem
        result = image_engine.process_image(
            image=image,
            operations=[op.dict() for op in request.operations],
            output_format=request.output_format
        )
        
        # Converter resultado para bytes
        output = io.BytesIO()
        if request.output_format == "PIL":
            result.save(output, format="PNG")
        else:
            Image.fromarray(result).save(output, format="PNG")
            
        return {
            "processed_image": output.getvalue(),
            "format": request.output_format
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch")
async def batch_process(
    files: List[UploadFile] = File(...),
    request: ImageProcessingRequest = None,
    background_tasks: BackgroundTasks = None
):
    """
    Processa múltiplas imagens em batch.
    
    Args:
        files: Lista de arquivos de imagem
        request: Parâmetros do processamento
        background_tasks: Tarefas em background
        
    Returns:
        Lista de imagens processadas
    """
    try:
        results = []
        
        for file in files:
            # Ler imagem
            image_data = await file.read()
            image = Image.open(io.BytesIO(image_data))
            
            # Processar imagem
            result = image_engine.process_image(
                image=image,
                operations=[op.dict() for op in request.operations],
                output_format=request.output_format
            )
            
            # Converter resultado para bytes
            output = io.BytesIO()
            if request.output_format == "PIL":
                result.save(output, format="PNG")
            else:
                Image.fromarray(result).save(output, format="PNG")
                
            results.append({
                "filename": file.filename,
                "processed_image": output.getvalue(),
                "format": request.output_format
            })
            
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 