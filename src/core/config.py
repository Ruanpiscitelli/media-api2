"""
Configurações globais da aplicação.
Gerencia variáveis de ambiente e configurações do sistema.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Configurações da aplicação."""
    
    # Ambiente
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENV: str = os.getenv("ENV", "development")
    
    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_WORKERS: int = int(os.getenv("API_WORKERS", "1"))
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "300"))
    
    # Diretórios
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    LOG_DIR: Path = BASE_DIR / "logs"
    MEDIA_DIR: Path = BASE_DIR / "media"
    TEMP_DIR: Path = BASE_DIR / "temp"
    MODELS_DIR: Path = BASE_DIR / "models"
    
    # Diretórios Suno
    SUNO_OUTPUT_DIR: Path = MEDIA_DIR / "suno"
    SUNO_CACHE_DIR: Path = TEMP_DIR / "suno"
    
    # Diretórios Shorts
    SHORTS_OUTPUT_DIR: Path = MEDIA_DIR / "shorts"
    SHORTS_CACHE_DIR: Path = TEMP_DIR / "shorts"
    SHORTS_UPLOAD_DIR: Path = TEMP_DIR / "uploads" / "shorts"
    
    # GPU
    CUDA_VISIBLE_DEVICES: Optional[str] = os.getenv("CUDA_VISIBLE_DEVICES")
    RENDER_TIMEOUT_SECONDS: int = int(os.getenv("RENDER_TIMEOUT_SECONDS", "600"))
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # ComfyUI
    COMFY_SERVER_HOST: str = os.getenv("COMFY_SERVER_HOST", "localhost")
    COMFY_SERVER_PORT: int = int(os.getenv("COMFY_SERVER_PORT", "8188"))
    COMFY_WEBSOCKET_PORT: int = int(os.getenv("COMFY_WEBSOCKET_PORT", "8188"))
    
    class Config:
        """Configurações do Pydantic."""
        env_file = ".env"
        case_sensitive = True

# Instância global das configurações
settings = Settings() 