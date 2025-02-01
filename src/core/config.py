"""
Configurações globais da aplicação.
"""
from pydantic_settings import BaseSettings
import os
from pathlib import Path
from typing import Optional, List
import torch
from pydantic import validator
from functools import lru_cache

class EnvironmentSettings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "development_key"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    BACKEND_CORS_ORIGINS: str = '["*"]'
    LOG_LEVEL: str = "debug"
    PROJECT_NAME: str = "Media API"
    VERSION: str = "2.0.0"
    API_V2_STR: str = "/api/v2"
    DATABASE_URL: str = "sqlite:///./sql_app.db"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REDIS_TIMEOUT: int = 5
    REDIS_SSL: bool = False
    RATE_LIMIT_PER_MINUTE: int = 60
    MEMORY_THRESHOLD_MB: int = 8192
    TEMP_FILE_MAX_AGE: int = 3600
    COMFY_API_URL: str = "http://localhost:8188/api"
    COMFY_WS_URL: str = "ws://localhost:8188/ws"
    COMFY_TIMEOUT: int = 30
    MAX_CONCURRENT_RENDERS: int = 4
    MAX_RENDER_TIME: int = 300
    MAX_VIDEO_LENGTH: int = 300
    MAX_VIDEO_SIZE: int = 100000000
    RENDER_TIMEOUT_SECONDS: int = 300

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"

class Settings(BaseSettings):
    env_settings: EnvironmentSettings

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        env = EnvironmentSettings()
        for field in env.__fields__:
            setattr(self, field, getattr(env, field))

    def check_config(self):
        """Valida configurações essenciais"""
        if not self.REDIS_PASSWORD:
            raise ValueError("Senha do Redis não configurada")
        if self.MAX_CONCURRENT_RENDERS < 1:
            raise ValueError("MAX_CONCURRENT_RENDERS deve ser maior que 0")
        # Adicionar outras validações necessárias

    @validator("DATABASE_URL")
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL não pode estar vazio")
        return v

    @validator("TEMP_DIR", "SUNO_OUTPUT_DIR", "SUNO_CACHE_DIR", "SHORTS_OUTPUT_DIR")
    def validate_directories(cls, v: Path) -> Path:
        if not v.exists():
            v.mkdir(parents=True, exist_ok=True)
        if not os.access(v, os.W_OK):
            raise ValueError(f"Directory {v} is not writable")
        return v

    @validator("REDIS_PASSWORD")
    def validate_redis_password(cls, v, values):
        env = values.get('ENVIRONMENT', 'development')
        if env == 'production' and not v:
            raise ValueError("Redis password is required in production")
        return v or "development_password"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()