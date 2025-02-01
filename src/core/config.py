"""
Configurações globais da aplicação.
"""
from pydantic_settings import BaseSettings
import os
from pathlib import Path

class Settings(BaseSettings):
    # Configurações básicas
    API_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Diretórios
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    TEMP_DIR: Path = Path("/workspace/temp")
    SUNO_OUTPUT_DIR: Path = Path("/workspace/outputs/suno")
    SUNO_CACHE_DIR: Path = Path("/workspace/cache/suno")
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    
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

    class Config:
        env_file = ".env"

settings = Settings()