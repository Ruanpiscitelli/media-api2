"""
Configurações da aplicação
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Configurações da API"""
    
    # Ambiente
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # Diretórios
    BASE_DIR: Path = Path("/workspace")
    MEDIA_DIR: Path = BASE_DIR / "media"
    CACHE_DIR: Path = BASE_DIR / "cache"
    MODELS_DIR: Path = BASE_DIR / "models"
    ASSETS_DIR: Path = BASE_DIR / "assets"
    TEMP_DIR: Path = BASE_DIR / "temp"
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    # Database
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "mediaapi"
    DATABASE_URL: str = "postgresql://user:password@localhost/dbname"
    DB_DEBUG: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    REDIS_MAX_CONNECTIONS: int = 10
    REDIS_TIMEOUT: int = 5
    
    # Modelos
    SDXL_MODEL_PATH: str = str(MODELS_DIR / "sdxl/sd_xl_base_1.0.safetensors")
    SDXL_VAE_PATH: str = str(MODELS_DIR / "sdxl/vae/sdxl_vae.safetensors")
    FISH_SPEECH_MODEL: str = str(MODELS_DIR / "fish_speech/fish_speech_model.pt")
    
    # Limites
    MAX_VIDEO_DURATION: int = 300  # 5 minutos
    MAX_VIDEO_SIZE: int = 100_000_000  # 100MB
    MAX_THREADS: int = 4
    
    # Debug
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = "INFO"
    
    # GPU
    GPU_MEMORY_FRACTION: float = 0.8
    GPU_TEMP_LIMIT: int = 85
    
    # Segurança
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Caminhos dos modelos
    MODELS_BASE_DIR: Path = BASE_DIR / "models"
    FISH_SPEECH_MODEL_PATH: str = os.getenv(
        "FISH_SPEECH_MODEL_PATH", 
        "/workspace/models/fish_speech/model.pt"
    )
    FISH_SPEECH_CONFIG_PATH: str = os.getenv(
        "FISH_SPEECH_CONFIG_PATH",
        "/workspace/models/fish_speech/config.json"
    )
    FISH_SPEECH_VOCAB_PATH: str = os.getenv(
        "FISH_SPEECH_VOCAB_PATH",
        "/workspace/models/fish_speech/vocab.json"
    )
    
    # Modo de desenvolvimento/teste
    TESTING: bool = os.getenv("TESTING", "False").lower() == "true"
    
    # Prometheus
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "9090"))
    
    # GPU Manager
    GPU_METRICS_PREFIX: str = os.getenv("GPU_METRICS_PREFIX", "gpu")
    GPU_POLL_INTERVAL: int = int(os.getenv("GPU_POLL_INTERVAL", "5"))
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "3600"))  # em segundos
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"  # Permite campos extras

# Instância global
settings = Settings()

# Criar diretórios necessários
for directory in [
    settings.MEDIA_DIR,
    settings.CACHE_DIR,
    settings.MODELS_DIR,
    settings.ASSETS_DIR,
    settings.TEMP_DIR,
    settings.LOGS_DIR
]:
    directory.mkdir(parents=True, exist_ok=True)