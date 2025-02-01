"""
Configurações para integração com ComfyUI.
"""
from typing import Optional
from pydantic_settings import BaseSettings
from pathlib import Path

class ComfyConfig(BaseSettings):
    """
    Configurações do ComfyUI.
    
    Carrega configurações de variáveis de ambiente com prefixo COMFY_.
    """
    
    # URLs
    host: str = "localhost"
    port: int = 8188
    api_url: str = f"http://{host}:{port}"
    ws_url: str = f"ws://{host}:{port}"
    
    # Diretórios
    base_dir: Path = Path("/app/comfy")
    models_dir: Path = base_dir / "models"
    workflows_dir: Path = base_dir / "workflows"
    outputs_dir: Path = base_dir / "outputs"
    
    # Timeouts (segundos)
    default_timeout: float = 300.0
    connection_timeout: float = 30.0
    websocket_timeout: float = 60.0
    
    # Cache
    cache_dir: Path = base_dir / "cache"
    max_cache_size: int = 10 * 1024 * 1024 * 1024  # 10GB
    cache_ttl: int = 24 * 60 * 60  # 24 horas
    
    # Recursos
    max_batch_size: int = 4
    max_concurrent_executions: int = 8
    min_free_vram: int = 2 * 1024 * 1024 * 1024  # 2GB
    
    # Retry
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        """Configurações do Pydantic"""
        env_prefix = "COMFY_"
        case_sensitive = False
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Cria diretórios se não existirem
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    @property
    def api_base_url(self) -> str:
        """URL base da API"""
        return f"{self.api_url}/api"
        
    @property
    def ws_base_url(self) -> str:
        """URL base do WebSocket"""
        return f"{self.ws_url}/ws"
        
    def get_model_path(self, model_name: str) -> Path:
        """Retorna caminho para um modelo"""
        return self.models_dir / model_name
        
    def get_workflow_path(self, workflow_name: str) -> Path:
        """Retorna caminho para um workflow"""
        return self.workflows_dir / f"{workflow_name}.json"
        
    def get_output_path(self, execution_id: str) -> Path:
        """Retorna caminho para outputs de uma execução"""
        return self.outputs_dir / execution_id
        
    def get_cache_path(self, cache_key: str) -> Path:
        """Retorna caminho para um item do cache"""
        return self.cache_dir / cache_key 