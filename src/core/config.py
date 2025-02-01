"""
Configurações globais da aplicação.
"""
from pydantic_settings import BaseSettings
import os
from pathlib import Path
from typing import Optional, List, Union
from pydantic import Field, validator
from functools import lru_cache
import json

class Settings(BaseSettings):
    # Ambiente
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    
    # Básico
    PROJECT_NAME: str = Field(default="Media API")
    VERSION: str = Field(default="2.0.0")
    API_V2_STR: str = Field(default="/api/v2")
    
    # Segurança
    SECRET_KEY: str = Field(default="development_key")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./sql_app.db")
    
    # Redis
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: str = Field(default="development_password")
    REDIS_DB: int = Field(default=0)
    REDIS_TIMEOUT: int = Field(default=5)
    REDIS_SSL: bool = Field(default=False)
    
    # CORS
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = Field(default='["*"]')
    
    # Logging
    LOG_LEVEL: str = Field(default="debug")
    
    # Limites
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    MEMORY_THRESHOLD_MB: int = Field(default=8192)
    TEMP_FILE_MAX_AGE: int = Field(default=3600)
    
    # ComfyUI
    COMFY_API_URL: str = Field(default="http://localhost:8188/api")
    COMFY_WS_URL: str = Field(default="ws://localhost:8188/ws")
    COMFY_TIMEOUT: int = Field(default=30)
    
    # Renderização
    MAX_CONCURRENT_RENDERS: int = Field(default=4)
    MAX_RENDER_TIME: int = Field(default=300)
    MAX_VIDEO_LENGTH: int = Field(default=300)
    MAX_VIDEO_SIZE: int = Field(default=100000000)
    RENDER_TIMEOUT_SECONDS: int = Field(default=300)
    
    # Diretórios
    TEMP_DIR: Path = Field(default=Path("/workspace/temp"))
    SUNO_OUTPUT_DIR: Path = Field(default=Path("/workspace/media/audio"))
    SUNO_CACHE_DIR: Path = Field(default=Path("/workspace/cache/suno"))
    SHORTS_OUTPUT_DIR: Path = Field(default=Path("/workspace/media/video"))

    @validator("REDIS_PASSWORD")
    def validate_redis_password(cls, v: str, values: dict) -> str:
        if values.get("ENVIRONMENT") == "production" and not v:
            raise ValueError("Redis password is required in production")
        return v or "development_password"

    @validator("DATABASE_URL")
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL não pode estar vazio")
        return v

    @validator("BACKEND_CORS_ORIGINS")
    def validate_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v

    @validator("TEMP_DIR", "SUNO_OUTPUT_DIR", "SUNO_CACHE_DIR", "SHORTS_OUTPUT_DIR")
    def validate_directories(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        if not os.access(v, os.W_OK):
            raise ValueError(f"Directory {v} is not writable")
        return v

    @validator("MAX_CONCURRENT_RENDERS")
    def validate_max_concurrent_renders(cls, v: int) -> int:
        if v < 1:
            raise ValueError("MAX_CONCURRENT_RENDERS deve ser maior que 0")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()