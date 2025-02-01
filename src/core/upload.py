"""
Gerenciamento seguro de uploads
"""
import aiofiles
import magic
import hashlib
from pathlib import Path
from fastapi import UploadFile, HTTPException
from typing import Set
import logging

logger = logging.getLogger(__name__)

ALLOWED_MIMETYPES: Set[str] = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'video/mp4',
    'audio/mpeg',
    'audio/wav'
}

MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB

async def validate_and_save_upload(
    file: UploadFile,
    upload_dir: Path
) -> Path:
    """Valida e salva upload com segurança"""
    
    # Verificar tamanho
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    
    if size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large"
        )
        
    # Ler conteúdo
    content = await file.read()
    
    # Verificar tipo MIME real
    mime_type = magic.from_buffer(content, mime=True)
    if mime_type not in ALLOWED_MIMETYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {mime_type}"
        )
        
    # Gerar nome seguro
    file_hash = hashlib.sha256(content).hexdigest()
    extension = Path(file.filename).suffix
    safe_filename = f"{file_hash}{extension}"
    
    # Salvar arquivo
    file_path = upload_dir / safe_filename
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
        
    return file_path 