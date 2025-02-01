"""
Script para configurar o ambiente ComfyUI, baixar modelos necessários e instalar nós customizados.
"""

import os
import sys
import subprocess
import requests
from pathlib import Path
import logging
import shutil

logger = logging.getLogger(__name__)

class ComfyUISetup:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent.parent
        self.comfy_path = self.base_path / "ComfyUI"
        self.models_path = self.base_path / "models"
        self.custom_nodes_path = self.base_path / "custom_nodes"
        
        # Configurar diretórios de modelos
        self.model_paths = {
            "checkpoints": self.models_path / "checkpoints",
            "vae": self.models_path / "vae",
            "loras": self.models_path / "loras",
            "fish_speech": self.models_path / "fish_speech",
            "fasthunyuan": self.models_path / "fasthunyuan"
        }

    def setup(self):
        """Configura todo o ambiente ComfyUI"""
        logger.info("🚀 Iniciando setup do ComfyUI...")
        
        # Criar diretórios
        self._create_directories()
        
        # Instalar dependências
        self._install_dependencies()
        
        # Configurar nós customizados
        self._setup_custom_nodes()
        
        # Configurar arquivo de configuração do ComfyUI
        self._setup_config()
        
        logger.info("✅ Setup do ComfyUI concluído!")

    def _create_directories(self):
        """Cria a estrutura de diretórios necessária"""
        # Criar diretórios de modelos
        for dir_path in self.model_paths.values():
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Criado diretório: {dir_path}")
        
        # Criar outros diretórios necessários
        other_dirs = [
            self.base_path / "workflows",
            self.base_path / "outputs",
            self.base_path / "logs"
        ]
        
        for dir_path in other_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Criado diretório: {dir_path}")

    def _install_dependencies(self):
        """Instala dependências Python necessárias"""
        logger.info("📦 Instalando dependências...")
        
        # Instalar dependências do ComfyUI
        if (self.comfy_path / "requirements.txt").exists():
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r",
                str(self.comfy_path / "requirements.txt")
            ], check=True)
        
        # Instalar dependências adicionais para Fish Speech e FastHunyuan
        extra_packages = [
            "torch>=2.0.0",
            "torchaudio>=2.0.0",
            "transformers>=4.30.0",
            "ffmpeg-python>=0.2.0",
            "opencv-python>=4.8.0",
            "scipy>=1.11.0",
            "librosa>=0.10.0"
        ]
        
        for package in extra_packages:
            subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], check=True)

    def _setup_custom_nodes(self):
        """Configura os nós customizados"""
        logger.info("🔧 Configurando nós customizados...")
        
        # Criar link simbólico dos nós customizados para o ComfyUI
        comfy_custom_nodes = self.comfy_path / "custom_nodes"
        comfy_custom_nodes.mkdir(parents=True, exist_ok=True)
        
        for node_dir in self.custom_nodes_path.iterdir():
            if node_dir.is_dir():
                target_link = comfy_custom_nodes / node_dir.name
                if not target_link.exists():
                    try:
                        target_link.symlink_to(node_dir, target_is_directory=True)
                        logger.info(f"✅ Link criado para: {node_dir.name}")
                    except Exception as e:
                        logger.error(f"❌ Erro ao criar link para {node_dir.name}: {str(e)}")
                        # Se falhar criar link simbólico, copiar diretório
                        shutil.copytree(node_dir, target_link)
                        logger.info(f"✅ Copiado diretório: {node_dir.name}")

    def _setup_config(self):
        """Configura o arquivo de configuração do ComfyUI"""
        logger.info("⚙️ Configurando ComfyUI...")
        
        config = {
            "model_dir": str(self.models_path),
            "custom_nodes_dir": str(self.custom_nodes_path),
            "output_dir": str(self.base_path / "outputs"),
            "temp_dir": str(self.base_path / "temp"),
            "disable_cuda_malloc": False,
            "preview_method": "auto",
            "vram_optimization_level": 2,
            "extra_model_paths": {
                "fish_speech": str(self.model_paths["fish_speech"]),
                "fasthunyuan": str(self.model_paths["fasthunyuan"])
            }
        }
        
        config_file = self.comfy_path / "config.json"
        
        try:
            import json
            with open(config_file, "w") as f:
                json.dump(config, f, indent=4)
            logger.info("✅ Arquivo de configuração criado")
        except Exception as e:
            logger.error(f"❌ Erro ao criar arquivo de configuração: {str(e)}")

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    setup = ComfyUISetup()
    setup.setup()