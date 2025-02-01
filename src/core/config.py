"""
Configuração unificada da aplicação com validação via Pydantic.
"""

from typing import Dict, List, Optional
from pydantic import Field, field_validator, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os
import secrets
import logging

logger = logging.getLogger(__name__)

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
    
    model_config = SettingsConfigDict(
        env_prefix='GPU_',
        extra="allow"
    )

class RedisConfig(BaseSettings):
    """Configurações do Redis"""
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    password: Optional[str] = None
    ssl: bool = Field(default=False)
    socket_timeout: int = Field(default=5)
    retry_on_timeout: bool = Field(default=True)
    max_connections: int = Field(default=10)
    
    model_config = SettingsConfigDict(
        env_prefix='REDIS_',
        extra="allow"
    )

class CacheConfig(BaseSettings):
    """Configurações de cache"""
    ttl: int = Field(default=300, description="Tempo de vida padrão em segundos")
    max_size: int = Field(default=1000, description="Número máximo de itens em cache")
    redis: RedisConfig = Field(default_factory=RedisConfig)
    
    model_config = SettingsConfigDict(
        env_prefix='CACHE_',
        extra="allow"
    )

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
    
    model_config = SettingsConfigDict(
        env_prefix='QUEUE_',
        extra="allow"
    )

class SecurityConfig(BaseSettings):
    """Configurações de segurança"""
    secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Chave secreta para JWT"
    )
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
    
    model_config = SettingsConfigDict(
        env_prefix='SECURITY_',
        extra="allow"
    )

class PathConfig(BaseSettings):
    """Configurações de caminhos"""
    workspace: Path = Field(default=Path("/workspace"))
    models: Path = Field(default=Path("/models"))
    temp: Path = Field(default=Path("/tmp"))
    logs: Path = Field(default=Path("/logs"))
    
    @field_validator("*")
    @classmethod
    def create_dirs(cls, v):
        if isinstance(v, Path):
            v.mkdir(parents=True, exist_ok=True)
        return v
    
    model_config = SettingsConfigDict(
        env_prefix='PATH_',
        extra="allow"
    )

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
    
    model_config = SettingsConfigDict(
        env_prefix='MODEL_',
        extra="allow"
    )

class Settings(BaseSettings):
    """Configuração global da aplicação"""
    
    # Ambiente
    environment: str = Field(default="development")
    debug: bool = Field(default=True)
    testing: bool = Field(default=False)
    
    # API
    project_name: str = Field(default="Media API")
    version: str = Field(default="2.0.0")
    api_v2_str: str = Field(default="/api/v2")
    
    # Servidor
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    workers: int = Field(default=1)
    MAX_CONNECTIONS: int = Field(default=1000)
    KEEP_ALIVE: int = Field(default=65)
    GRACEFUL_SHUTDOWN_TIMEOUT: int = Field(default=60)
    REQUEST_TIMEOUT: int = Field(default=30)  # timeout padrão
    LONG_TIMEOUT: int = Field(default=300)    # timeout para operações longas
    
    # Database
    DATABASE_URL: str = "sqlite:///./sql_app.db"
    SQL_DEBUG: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_SSL: bool = Field(default=False)
    REDIS_TIMEOUT: int = Field(default=5)
    
    # Rate Limiting
    RATE_LIMIT_DEFAULT: int = Field(default=100)  # requisições por hora
    RATE_LIMIT_BURST: int = Field(default=10)     # requisições por minuto
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_WINDOW: int = Field(default=3600)  # janela em segundos
    RATE_LIMIT_MAX: int = Field(default=1000)     # máximo por IP
    
    # Security
    secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Chave secreta para JWT"
    )
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    backend_cors_origins: List[str] = Field(default=["*"])
    
    # Resources
    memory_threshold_mb: int = Field(default=8192)
    temp_file_max_age: int = Field(default=3600)
    
    # ComfyUI
    COMFY_API_URL: str = "http://localhost:8188"
    COMFY_WS_URL: str = "ws://localhost:8188/ws"
    COMFY_TIMEOUT: int = 30
    COMFY_API_KEY: Optional[str] = None
    max_concurrent_renders: int = Field(default=4)
    max_render_time: int = Field(default=300)
    max_video_length: int = Field(default=300)
    max_video_size: int = Field(default=100000000)
    render_timeout_seconds: int = Field(default=300)
    
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
    
    # Adicionar atributo faltando
    MEDIA_DIR: Path = Field(default=Path("/workspace/media"))
    MAX_THREADS: int = Field(default=32)
    
    # Configurações de modelos
    MODELS_DIR: Path = Field(default=Path("/workspace/models"))
    SDXL_MODEL_PATH: Optional[Path] = Field(
        default=None,
        description="Caminho para modelo SDXL"
    )
    SDXL_VAE_PATH: Optional[Path] = Field(
        default=None,
        description="Caminho para VAE do SDXL"
    )
    
    # FFmpeg
    FFMPEG_BINARY: str = Field(
        default="ffmpeg",
        description="Caminho para binário do FFmpeg"
    )
    FFMPEG_THREADS: int = Field(
        default=0,  # 0 = auto
        description="Número de threads para FFmpeg"
    )
    FFMPEG_HWACCEL: str = Field(
        default="cuda",
        description="Aceleração de hardware (cuda, nvenc, none)"
    )
    
    # Fish Speech
    FISH_SPEECH_MODEL: Optional[Path] = Field(
        default=None,
        description="Caminho para modelo Fish Speech"
    )
    FISH_SPEECH_SAMPLE_RATE: int = Field(
        default=22050,
        description="Sample rate para síntese"
    )
    FISH_SPEECH_MAX_LENGTH: int = Field(
        default=1000,
        description="Comprimento máximo do texto"
    )
    
    @validator("SDXL_MODEL_PATH", "SDXL_VAE_PATH", "FISH_SPEECH_MODEL")
    def validate_model_paths(cls, v, values):
        # Em desenvolvimento, permitir caminhos não existentes
        if values.get("ENVIRONMENT") == "development":
            return v
        # Em produção, validar caminhos
        if not v or not v.exists():
            raise ValueError(f"Arquivo de modelo não encontrado: {v}")
        return v
    
    @property
    def REDIS_URL(self) -> str:
        """Gera URL de conexão Redis"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    def check_config(self):
        """Valida configurações críticas"""
        # Validar ambiente
        if self.environment not in ['development', 'staging', 'production']:
            raise ValueError(f"Ambiente inválido: {self.environment}")
            
        # Validar timeouts
        if self.REQUEST_TIMEOUT >= self.LONG_TIMEOUT:
            raise ValueError("REQUEST_TIMEOUT deve ser menor que LONG_TIMEOUT")
            
        # Validar rate limits
        if self.RATE_LIMIT_BURST > self.RATE_LIMIT_DEFAULT:
            raise ValueError("BURST limit não pode ser maior que DEFAULT limit")
        
        # Validar URLs
        if not self.COMFY_API_URL.startswith(('http://', 'https://')):
            raise ValueError("COMFY_API_URL deve começar com http:// ou https://")
    
    @validator("RATE_LIMIT_BURST")
    def validate_rate_limits(cls, v, values):
        if v > values["RATE_LIMIT_DEFAULT"]:
            raise ValueError(
                "RATE_LIMIT_BURST não pode ser maior que RATE_LIMIT_DEFAULT"
            )
        return v
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
        use_enum_values=True
    )

def validate_models():
    """Verifica se os modelos necessários estão presentes"""
    models_to_check = [
        (settings.SDXL_MODEL_PATH, "SDXL Base Model"),
        (settings.SDXL_VAE_PATH, "SDXL VAE"),
        (settings.FISH_SPEECH_MODEL, "Fish Speech Model")
    ]
    
    for model_path, model_name in models_to_check:
        if not Path(model_path).exists():
            logger.warning(f"Modelo {model_name} não encontrado em {model_path}")
            return False
    return True

# Instância global de configuração
settings = Settings()