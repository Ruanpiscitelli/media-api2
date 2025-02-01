"""
Configurações da aplicação
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Configurações da API"""
    
    # Diretórios
    BASE_DIR: Path = Path("/workspace")
    MEDIA_DIR: Path = BASE_DIR / "media"
    CACHE_DIR: Path = BASE_DIR / "cache"
    MODELS_DIR: Path = BASE_DIR / "models"
    ASSETS_DIR: Path = BASE_DIR / "assets"
    TEMP_DIR: Path = BASE_DIR / "temp"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 10
    REDIS_TIMEOUT: int = 5
    
    # Limites
    MAX_VIDEO_DURATION: int = 300  # 5 minutos
    MAX_VIDEO_SIZE: int = 100_000_000  # 100MB
    MAX_THREADS: int = 4
    
    # Debug
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # GPU
    GPU_MEMORY_FRACTION: float = 0.8
    GPU_TEMP_LIMIT: int = 85
    
    class Config:
        env_file = ".env"

# Instância global
settings = Settings()

# Criar diretórios necessários
for directory in [
    settings.MEDIA_DIR,
    settings.CACHE_DIR,
    settings.MODELS_DIR,
    settings.ASSETS_DIR,
    settings.TEMP_DIR
]:
    directory.mkdir(parents=True, exist_ok=True)