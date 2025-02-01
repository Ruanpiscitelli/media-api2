"""
Gerenciador de modelos para download e configuração automática.
Responsável por baixar e configurar todos os modelos necessários.
"""

import asyncio
import logging
from pathlib import Path
import aiohttp
from tqdm import tqdm
import os
import zipfile
import tarfile
import shutil
import torch
from safetensors.torch import load_file
from typing import Dict, List, Optional
from src.core.config import settings

logger = logging.getLogger(__name__)

class ModelConfig:
    """Configuração para um modelo."""
    def __init__(
        self,
        name: str,
        url: str,
        path: Path,
        required: bool = True,
        metadata: Dict = None
    ):
        self.name = name
        self.url = url
        self.path = path
        self.required = required
        self.metadata = metadata or {}
        self.is_downloaded = False

class ModelManager:
    """
    Gerenciador de modelos.
    Implementa download e configuração automática de modelos.
    """
    
    def __init__(self, models_dir: str = None):
        """
        Inicializa o gerenciador de modelos.
        
        Args:
            models_dir: Diretório base para os modelos
        """
        self.models_dir = Path(models_dir or settings.MODELS_DIR)
        self.models: Dict[str, ModelConfig] = {}
        self._setup_model_configs()
        
    def _setup_model_configs(self):
        """Configura os modelos necessários."""
        # SDXL
        self.models["sdxl_base"] = ModelConfig(
            name="SDXL Base",
            url="https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors",
            path=self.models_dir / "stable-diffusion/sdxl_base.safetensors",
            required=True
        )
        
        self.models["sdxl_refiner"] = ModelConfig(
            name="SDXL Refiner",
            url="https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors",
            path=self.models_dir / "stable-diffusion/sdxl_refiner.safetensors",
            required=False
        )
        
        self.models["sdxl_vae"] = ModelConfig(
            name="SDXL VAE",
            url="https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors",
            path=self.models_dir / "stable-diffusion/sdxl_vae.safetensors",
            required=True
        )
        
        # Fish Speech
        self.models["fish_speech_base"] = ModelConfig(
            name="Fish Speech Base",
            url="https://huggingface.co/fishaudio/fish-speech/resolve/main/base_speakers.pth",
            path=self.models_dir / "fish_speech/base_speakers.pth",
            required=True
        )
        
        self.models["fish_speech_voices"] = ModelConfig(
            name="Fish Speech Voices",
            url="https://huggingface.co/fishaudio/fish-speech/resolve/main/voices.zip",
            path=self.models_dir / "fish_speech/voices",
            required=True
        )
        
        # FastHuayuan
        self.models["fasthuayuan_base"] = ModelConfig(
            name="FastHuayuan Base",
            url="https://github.com/fasthuayuan/video-generation/releases/download/v1.0/fasthuayuan_base.pth",
            path=self.models_dir / "fasthuayuan/base_model.pth",
            required=True
        )
        
        self.models["fasthuayuan_config"] = ModelConfig(
            name="FastHuayuan Config",
            url="https://raw.githubusercontent.com/fasthuayuan/video-generation/main/configs/base_config.json",
            path=self.models_dir / "fasthuayuan/config.json",
            required=True
        )
        
        # ComfyUI Models
        self.models["controlnet_canny"] = ModelConfig(
            name="ControlNet Canny",
            url="https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11p_sd15_canny.pth",
            path=self.models_dir / "comfyui/controlnet/control_v11p_sd15_canny.pth",
            required=False
        )
        
        self.models["realesrgan"] = ModelConfig(
            name="RealESRGAN",
            url="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
            path=self.models_dir / "comfyui/upscalers/RealESRGAN_x4plus.pth",
            required=False
        )
    
    async def download_model(self, model_config: ModelConfig):
        """
        Baixa um modelo específico.
        
        Args:
            model_config: Configuração do modelo
        """
        try:
            # Criar diretório pai se não existir
            model_config.path.parent.mkdir(parents=True, exist_ok=True)
            
            # Verificar se já existe
            if model_config.path.exists():
                logger.info(f"Modelo {model_config.name} já existe")
                model_config.is_downloaded = True
                return
            
            logger.info(f"Baixando modelo {model_config.name}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(model_config.url) as response:
                    if response.status != 200:
                        raise Exception(f"Erro ao baixar modelo: {response.status}")
                    
                    total_size = int(response.headers.get('content-length', 0))
                    
                    # Configurar barra de progresso
                    progress = tqdm(
                        total=total_size,
                        desc=f"Baixando {model_config.name}",
                        unit='iB',
                        unit_scale=True
                    )
                    
                    temp_path = model_config.path.with_suffix('.temp')
                    
                    # Baixar arquivo
                    with open(temp_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            progress.update(len(chunk))
                    
                    # Processar arquivo baseado na extensão
                    if str(model_config.path).endswith('.zip'):
                        with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                            zip_ref.extractall(model_config.path.parent)
                    elif str(model_config.path).endswith('.tar.gz'):
                        with tarfile.open(temp_path, 'r:gz') as tar_ref:
                            tar_ref.extractall(model_config.path.parent)
                    else:
                        shutil.move(temp_path, model_config.path)
                    
                    progress.close()
                    model_config.is_downloaded = True
                    logger.info(f"Download de {model_config.name} concluído!")
                    
        except Exception as e:
            logger.error(f"Erro ao baixar {model_config.name}: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    async def verify_model(self, model_config: ModelConfig) -> bool:
        """
        Verifica a integridade de um modelo.
        
        Args:
            model_config: Configuração do modelo
            
        Returns:
            bool: True se o modelo está íntegro
        """
        try:
            if not model_config.path.exists():
                return False
                
            if str(model_config.path).endswith('.pth'):
                # Verificar modelo PyTorch
                model = torch.load(model_config.path, map_location='cpu')
                return True
            elif str(model_config.path).endswith('.safetensors'):
                # Verificar modelo Safetensors
                _ = load_file(model_config.path)
                return True
            return True
            
        except Exception as e:
            logger.error(f"Erro na verificação de {model_config.name}: {e}")
            return False
    
    async def setup_system(self):
        """Configura todo o sistema, baixando e verificando modelos."""
        logger.info("Iniciando configuração do sistema...")
        
        # Criar diretórios base
        self.create_directories()
        
        # Baixar todos os modelos necessários
        tasks = []
        for model in self.models.values():
            if model.required:
                tasks.append(self.download_model(model))
        
        # Executar downloads em paralelo
        await asyncio.gather(*tasks)
        
        # Verificar integridade
        for model in self.models.values():
            if model.required and not await self.verify_model(model):
                raise Exception(f"Falha na verificação do modelo {model.name}")
        
        logger.info("Configuração do sistema concluída!")
    
    def create_directories(self):
        """Cria estrutura de diretórios necessária."""
        directories = [
            self.models_dir / "stable-diffusion",
            self.models_dir / "fish_speech" / "voices",
            self.models_dir / "fasthuayuan",
            self.models_dir / "comfyui" / "controlnet",
            self.models_dir / "comfyui" / "upscalers"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_model_info(self, name: str) -> Optional[Dict]:
        """
        Retorna informações sobre um modelo.
        
        Args:
            name: Nome do modelo
            
        Returns:
            Dict: Informações do modelo
        """
        if name not in self.models:
            return None
            
        model = self.models[name]
        return {
            'name': model.name,
            'path': str(model.path),
            'required': model.required,
            'is_downloaded': model.is_downloaded,
            'metadata': model.metadata
        }
    
    def list_models(self, filter_downloaded: bool = False) -> List[Dict]:
        """
        Lista todos os modelos disponíveis.
        
        Args:
            filter_downloaded: Se True, retorna apenas modelos baixados
            
        Returns:
            List[Dict]: Lista de informações dos modelos
        """
        models = []
        for name, model in self.models.items():
            if not filter_downloaded or model.is_downloaded:
                models.append(self.get_model_info(name))
        return models

# Instância global do gerenciador
model_manager = ModelManager() 