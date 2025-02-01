"""
Configurações específicas para o serviço de shorts.
"""
from pathlib import Path

SHORTS_CONFIG = {
    "OUTPUT_DIR": Path("/workspace/outputs/shorts"),
    "CACHE_DIR": Path("/workspace/cache/shorts"),
    "UPLOAD_DIR": Path("/workspace/uploads/shorts"),
}