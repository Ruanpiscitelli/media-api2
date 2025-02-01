"""
Configuração unificada da aplicação com validação via Pydantic.
"""

from typing import Dict, List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os

class GPUConfig(BaseSettings):
    """Configurações de GPU"""
    devices: List[int] = Field(default=[0,1,2,3], description="IDs das GPUs disponíveis")
    temperature_limit: int = Field(default=85, description="Limite de temperatura em °C")
    utilization_threshold: int = Field(default=95, description="Limite de utilização em %")
    memory_headroom: int = Field(default=1024, description="Margem de segurança de VRAM em MB")
    metrics_interval: int = Field(default=1, description="Intervalo de coleta de métricas em segundos")
    
    optimization: Dict = Field(default={
        "enable_tf32": True,
        "enable_cudnn_benchmarks": True
    })
    
    priorities: Dict[str, List[int]] = Field(default={
        "image": [0, 1],      # GPUs 0,1 prioritárias para imagem
        "speech": [2],        # GPU 2 prioritária para áudio
        "video": [3]          # GPU 3 prioritária para vídeo
    })
    
    model_config = SettingsConfigDict(env_prefix='GPU_')

class RedisConfig(BaseSettings):
    """Configurações do Redis"""
    host: str = Field(default="localhost", env='REDIS_HOST')
    port: int = Field(default=6379, env='REDIS_PORT')
    db: int = Field(default=0, env='REDIS_DB')
    password: Optional[str] = Field(default=None, env='REDIS_PASSWORD')
    ssl: bool = Field(default=False, env='REDIS_SSL')
    socket_timeout: int = Field(default=5, env='REDIS_TIMEOUT')
    retry_on_timeout: bool = Field(default=True)
    max_connections: int = Field(default=10)
    
    model_config = SettingsConfigDict(env_prefix='REDIS_')

class CacheConfig(BaseSettings):
    """Configurações de cache"""
    ttl: int = Field(default=300, description="Tempo de vida padrão em segundos")
    max_size: int = Field(default=1000, description="Número máximo de itens em cache")
    
    redis: RedisConfig = Field(default_factory=RedisConfig)
    
    model_config = SettingsConfigDict(env_prefix='CACHE_')

class QueueConfig(BaseSettings):
    """Configurações de fila"""
    max_size: int = Field(default=1000)
    timeout: int = Field(default=30)
    retry_delay: int = Field(default=5)
    max_retries: int = Field(default=3)
    
    priorities: Dict[str, int] = Field(default={
        "realtime": 3,
        "high": 2,
        "normal": 1,
        "low": 0
    })
    
    model_config = SettingsConfigDict(env_prefix='QUEUE_')

class SecurityConfig(BaseSettings):
    """Configurações de segurança"""
    secret_key: str = Field(default="your-secret-key-here")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    
    rate_limits: Dict[str, Dict] = Field(default={
        "default": {
            "calls": 100,
            "period": 60
        },
        "image": {
            "calls": 50,
            "period": 60
        },
        "video": {
            "calls": 10,
            "period": 60
        }
    })
    
    model_config = SettingsConfigDict(env_prefix='SECURITY_')

class PathConfig(BaseSettings):
    """Configurações de caminhos"""
    workspace: Path = Field(default=Path("/workspace"))
    models: Path = Field(default=Path("/models"))
    temp: Path = Field(default=Path("/tmp"))
    logs: Path = Field(default=Path("/logs"))
    
    @validator("*")
    def create_dirs(cls, v):
        if isinstance(v, Path):
            v.mkdir(parents=True, exist_ok=True)
        return v
    
    model_config = SettingsConfigDict(env_prefix='PATH_')

class ModelConfig(BaseSettings):
    """Configurações de modelos"""
    sdxl_path: Path = Field(default=Path("/models/sdxl"))
    fish_speech_path: Path = Field(default=Path("/models/fish_speech"))
    upscaler_path: Path = Field(default=Path("/models/upscaler"))
    
    vram_requirements: Dict[str, float] = Field(default={
        "sdxl": 8.5,
        "fish_speech": 4.2,
        "upscaler": 2.0
    })
    
    model_config = SettingsConfigDict(env_prefix='MODEL_')

class Settings(BaseSettings):
    """Configuração global da aplicação"""
    
    # Ambiente
    env: str = Field(default="development")
    debug: bool = Field(default=True)
    testing: bool = Field(default=False)
    
    # Servidor
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    workers: int = Field(default=1)
    
    # Logging
    log_level: str = Field(default="INFO")
    json_logs: bool = Field(default=False)
    
    # Componentes
    gpu: GPUConfig = Field(default_factory=GPUConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    queue: QueueConfig = Field(default_factory=QueueConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
    models: ModelConfig = Field(default_factory=ModelConfig)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix=""
    )

# Instância global de configuração
settings = Settings()