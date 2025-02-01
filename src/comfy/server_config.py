"""
Configuração do servidor ComfyUI.
"""

import os
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel

class ComfyUIConfig(BaseModel):
    """Configuração do servidor ComfyUI"""
    host: str = "0.0.0.0"
    port: int = 8188
    models_dir: Path = Path("models")
    outputs_dir: Path = Path("outputs")
    enable_cors: bool = True
    cors_origins: str = "*"
    enable_api: bool = True
    gpu_only: bool = True
    extra_model_paths: Dict[str, Path] = {
        "stable-diffusion": Path("models/stable-diffusion"),
        "lora": Path("models/lora"),
        "vae": Path("models/vae"),
        "embeddings": Path("models/embeddings")
    }

class ComfyUIServer:
    """Gerenciador do servidor ComfyUI"""
    
    def __init__(self, config: Optional[ComfyUIConfig] = None):
        """Inicializa o servidor ComfyUI"""
        self.config = config or ComfyUIConfig()
        
    def get_start_command(self) -> str:
        """Retorna comando para iniciar o servidor"""
        cmd_parts = [
            "python main.py",
            f"--host {self.config.host}",
            f"--port {self.config.port}",
            "--listen"
        ]
        
        if self.config.enable_cors:
            cmd_parts.append("--enable-cors")
            cmd_parts.append(f"--cors-origins {self.config.cors_origins}")
            
        if self.config.enable_api:
            cmd_parts.append("--enable-api")
            
        if self.config.gpu_only:
            cmd_parts.append("--gpu-only")
            
        for model_type, path in self.config.extra_model_paths.items():
            cmd_parts.append(f"--extra-model-paths {path}")
            
        return " ".join(cmd_parts)
        
    def ensure_directories(self):
        """Garante que os diretórios necessários existem"""
        # Criar diretórios de modelos
        for path in self.config.extra_model_paths.values():
            path.mkdir(parents=True, exist_ok=True)
            
        # Criar diretório de outputs
        self.config.outputs_dir.mkdir(parents=True, exist_ok=True)
        
    def get_nginx_config(self) -> str:
        """Retorna configuração nginx para proxy reverso"""
        return f"""
server {{
    listen 80;
    server_name $server_name;

    location /comfy/ {{
        proxy_pass http://{self.config.host}:{self.config.port}/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}
}}
"""

# Instância global do servidor
comfy_server = ComfyUIServer() 