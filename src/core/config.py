"""
Configurações globais da aplicação.
"""
from pydantic_settings import BaseSettings
import os
from pathlib import Path
from typing import Optional
import torch

class Settings(BaseSettings):
    # Configurações básicas
    API_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Diretórios
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    TEMP_DIR: Path = Path("/workspace/temp")
    SUNO_OUTPUT_DIR: Path = Path("/workspace/outputs/suno")
    SUNO_CACHE_DIR: Path = Path("/workspace/cache/suno")
    SHORTS_OUTPUT_DIR: Path = Path("/workspace/outputs/shorts")
    SHORTS_CACHE_DIR: Path = Path("/workspace/cache/shorts")
    SHORTS_UPLOAD_DIR: Path = Path("/workspace/uploads/shorts")
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_TIMEOUT: int = int(os.getenv("REDIS_TIMEOUT", "5"))  # segundos
    REDIS_SSL: bool = os.getenv("REDIS_SSL", "false").lower() == "true"
    
    # Limites e Timeouts
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    MEMORY_THRESHOLD_MB: int = int(os.getenv("MEMORY_THRESHOLD_MB", "8192"))
    TEMP_FILE_MAX_AGE: int = int(os.getenv("TEMP_FILE_MAX_AGE", "3600"))
    
    # ComfyUI
    COMFY_API_URL: str = os.getenv("COMFY_API_URL", "http://localhost:8188/api")
    COMFY_WS_URL: str = os.getenv("COMFY_WS_URL", "ws://localhost:8188/ws")
    COMFY_TIMEOUT: int = int(os.getenv("COMFY_TIMEOUT", "30"))
    
    # Auth
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # Adicionar novas configurações de renderização
    MAX_CONCURRENT_RENDERS: int = 4
    MAX_RENDER_TIME: int = 300  # segundos
    MAX_VIDEO_LENGTH: int = 300  # segundos
    MAX_VIDEO_SIZE: int = 100_000_000  # 100MB

    # Adicionar timeout de renderização
    RENDER_TIMEOUT_SECONDS: int = 300  # 5 minutos

    # Adicionar configurações de imagem
    IMAGE_OUTPUT_DIR: Path = Path("/workspace/outputs/images")
    IMAGE_CACHE_DIR: Path = Path("/workspace/cache/images")
    IMAGE_UPLOAD_DIR: Path = Path("/workspace/uploads/images")
    
    # Configurações de modelo de imagem
    IMAGE_MODEL_PATH: Optional[str] = None
    IMAGE_MODEL_DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"

    def check_config(self):
        """Valida configurações essenciais"""
        if not self.REDIS_PASSWORD:
            raise ValueError("Senha do Redis não configurada")
        if self.MAX_CONCURRENT_RENDERS < 1:
            raise ValueError("MAX_CONCURRENT_RENDERS deve ser maior que 0")
        # Adicionar outras validações necessárias

    class Config:
        env_file = ".env"

settings = Settings()