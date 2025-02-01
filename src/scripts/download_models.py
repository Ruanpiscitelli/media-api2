"""
Script para baixar modelos necessários do Hugging Face.
"""

import os
import sys
from pathlib import Path
import requests
from tqdm import tqdm
import logging
import hashlib
import json
import subprocess

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ModelDownloader:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent.parent
        self.models_path = self.base_path / "models"
        self.custom_nodes_path = self.base_path / "custom_nodes"
        
        # Token do Hugging Face (opcional)
        self.hf_token = os.getenv("HUGGINGFACE_TOKEN")
        if not self.hf_token:
            logger.warning("⚠️ HUGGINGFACE_TOKEN não definido. Alguns modelos podem falhar ao baixar.")
        
        # Configuração dos modelos
        self.models = {
            "sdxl_base": {
                "name": "SDXL 1.0 Base",
                "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0_0.9vae.safetensors",
                "path": "checkpoints/sd_xl_base_1.0.safetensors",
                "sha256": None,  # Será verificado durante o download
                "requires_auth": False
            },
            "sdxl_vae": {
                "name": "SDXL VAE",
                "url": "https://huggingface.co/madebyollin/sdxl-vae-fp16-fix/resolve/main/sdxl_vae.safetensors",
                "path": "vae/sdxl_vae.safetensors",
                "sha256": None,  # Será verificado durante o download
                "requires_auth": False
            },
            "fish_speech": {
                "name": "Fish Speech 2.0",
                "url": "https://huggingface.co/fishaudio/fish-speech-v2/resolve/main/model.safetensors",
                "path": "fish_speech/fish_speech_v2.safetensors",
                "sha256": None,  # Será verificado durante o download
                "requires_auth": True
            },
            "fast_hunyuan": {
                "name": "FastHunyuan",
                "url": "https://huggingface.co/FastVideo/FastHunyuan-mini/resolve/main/FastHunyuan-mini.safetensors",
                "path": "fasthunyuan/FastHunyuan-mini.safetensors",
                "sha256": None,  # Será verificado durante o download
                "requires_auth": True
            }
        }
        
        # Nós customizados necessários
        self.custom_nodes = {
            "ComfyUI-VideoHelperSuite": {
                "url": "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git",
                "branch": "main"
            },
            "ComfyUI-Manager": {
                "url": "https://github.com/ltdrdata/ComfyUI-Manager.git",
                "branch": "main"
            }
        }
    
    def download_file(self, url: str, dest_path: Path, desc: str = None, requires_auth: bool = False) -> bool:
        """
        Baixa um arquivo com barra de progresso.
        
        Args:
            url: URL do arquivo
            dest_path: Caminho de destino
            desc: Descrição para a barra de progresso
            requires_auth: Se requer autenticação no Hugging Face
            
        Returns:
            bool indicando sucesso
        """
        try:
            headers = {}
            if requires_auth and self.hf_token:
                headers["Authorization"] = f"Bearer {self.hf_token}"
            
            response = requests.get(url, stream=True, headers=headers)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            
            with tqdm(
                total=total_size,
                unit='iB',
                unit_scale=True,
                desc=desc
            ) as progress_bar:
                with open(dest_path, 'wb') as f:
                    for chunk in response.iter_content(block_size):
                        size = f.write(chunk)
                        progress_bar.update(size)
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao baixar {url}: {str(e)}")
            if dest_path.exists():
                dest_path.unlink()
            return False
    
    def verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        """
        Verifica o checksum SHA256 de um arquivo.
        
        Args:
            file_path: Caminho do arquivo
            expected_sha256: Hash SHA256 esperado
            
        Returns:
            bool indicando se o checksum está correto
        """
        if not expected_sha256:
            return True
            
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        actual_sha256 = sha256_hash.hexdigest()
        return actual_sha256 == expected_sha256
    
    def install_custom_nodes(self):
        """Instala os nós customizados necessários"""
        logger.info("🔧 Instalando nós customizados...")
        
        self.custom_nodes_path.mkdir(parents=True, exist_ok=True)
        
        for node_name, node_info in self.custom_nodes.items():
            node_path = self.custom_nodes_path / node_name
            
            if node_path.exists():
                logger.info(f"Atualizando {node_name}...")
                try:
                    subprocess.run(
                        ["git", "pull", "origin", node_info["branch"]],
                        cwd=str(node_path),
                        check=True
                    )
                except subprocess.CalledProcessError as e:
                    logger.error(f"Erro ao atualizar {node_name}: {str(e)}")
            else:
                logger.info(f"Clonando {node_name}...")
                try:
                    subprocess.run(
                        ["git", "clone", "-b", node_info["branch"], node_info["url"], str(node_path)],
                        check=True
                    )
                except subprocess.CalledProcessError as e:
                    logger.error(f"Erro ao clonar {node_name}: {str(e)}")
            
            # Instalar dependências do nó se existir requirements.txt
            requirements_file = node_path / "requirements.txt"
            if requirements_file.exists():
                logger.info(f"Instalando dependências para {node_name}...")
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                        check=True
                    )
                except subprocess.CalledProcessError as e:
                    logger.error(f"Erro ao instalar dependências de {node_name}: {str(e)}")
    
    def download_models(self):
        """Baixa todos os modelos necessários"""
        logger.info("🚀 Iniciando download dos modelos")
        
        # Criar diretórios
        for model in self.models.values():
            model_path = self.models_path / model["path"]
            model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Baixar modelos
        for model_id, model in self.models.items():
            model_path = self.models_path / model["path"]
            
            if model_path.exists():
                logger.info(f"Verificando checksum de {model['name']}...")
                if self.verify_checksum(model_path, model["sha256"]):
                    logger.info(f"✅ {model['name']} já existe e está íntegro")
                    continue
                else:
                    logger.warning(f"⚠️ Checksum inválido para {model['name']}, baixando novamente")
                    model_path.unlink()
            
            # Verificar se requer autenticação
            if model.get("requires_auth", False) and not self.hf_token:
                logger.warning(f"⚠️ Pulando {model['name']} pois requer autenticação no Hugging Face")
                continue
            
            logger.info(f"Baixando {model['name']}...")
            if self.download_file(model["url"], model_path, model["name"], model.get("requires_auth", False)):
                if self.verify_checksum(model_path, model["sha256"]):
                    logger.info(f"✅ {model['name']} baixado e verificado com sucesso")
                else:
                    logger.error(f"❌ Checksum inválido para {model['name']}")
                    model_path.unlink()
            else:
                logger.error(f"❌ Erro ao baixar {model['name']}")
    
    def save_model_info(self):
        """Salva informações dos modelos em JSON"""
        info_path = self.models_path / "models_info.json"
        
        model_info = {
            model_id: {
                "name": model["name"],
                "path": str(self.models_path / model["path"]),
                "sha256": model["sha256"]
            }
            for model_id, model in self.models.items()
        }
        
        with open(info_path, "w") as f:
            json.dump(model_info, f, indent=4)
        
        logger.info(f"✅ Informações dos modelos salvas em {info_path}")

def main():
    try:
        downloader = ModelDownloader()
        
        # Baixar modelos
        downloader.download_models()
        downloader.save_model_info()
        
        # Instalar nós customizados
        downloader.install_custom_nodes()
        
        logger.info("✨ Download dos modelos e instalação dos nós concluídos com sucesso")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 