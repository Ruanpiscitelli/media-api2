"""
Validação de modelos e pesos
"""
import hashlib
import aiofiles
from pathlib import Path
import logging
from typing import Dict

logger = logging.getLogger(__name__)

MODEL_CHECKSUMS = {
    'sdxl.safetensors': 'abc123...',  # Exemplo
    'fish_speech.pth': 'def456...'     # Exemplo
}

async def validate_model(model_path: Path) -> bool:
    """Valida checksum de um modelo"""
    if not model_path.exists():
        logger.error(f"Modelo não encontrado: {model_path}")
        return False
        
    # Calcular hash do arquivo
    sha256_hash = hashlib.sha256()
    async with aiofiles.open(model_path, 'rb') as f:
        while chunk := await f.read(8192):
            sha256_hash.update(chunk)
            
    # Verificar hash
    calculated_hash = sha256_hash.hexdigest()
    expected_hash = MODEL_CHECKSUMS.get(model_path.name)
    
    if not expected_hash:
        logger.warning(f"Hash não definido para: {model_path.name}")
        return False
        
    if calculated_hash != expected_hash:
        logger.error(
            f"Hash inválido para {model_path.name}. "
            f"Esperado: {expected_hash}, "
            f"Calculado: {calculated_hash}"
        )
        return False
        
    return True 