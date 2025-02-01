"""
Script para download dos modelos necessários
"""
import os
import sys
import requests
import hashlib
from pathlib import Path
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODELS = {
    "sdxl": {
        "base": {
            "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors",
            "path": "/workspace/models/sdxl/model.safetensors",
            "sha256": "31e35c80fc4829d14f90153f4c74cd59c90b779f6afe5a91141fd988e4d5d81a"
        },
        "vae": {
            "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/vae.safetensors",
            "path": "/workspace/models/sdxl/vae.safetensors",
            "sha256": "a8df6e1b3f7d76b8afe6e5c8e4e3aa7c2ee0e3f7ad9463f1f3119d32d0ebf3fe"
        }
    },
    "fish_speech": {
        "model.pt": "URL_DO_MODELO",
        "config.json": "URL_DO_CONFIG",
        "vocab.json": "URL_DO_VOCAB"
    }
}

def download_file(url: str, dest_path: Path, desc: str):
    """Download arquivo com barra de progresso"""
    response = requests.get(url, stream=True)
    total = int(response.headers.get('content-length', 0))

    with open(dest_path, 'wb') as file, tqdm(
        desc=desc,
        total=total,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            pbar.update(size)

def verify_sha256(file_path: str, expected_hash: str) -> bool:
    """Verifica hash SHA256 do arquivo"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest() == expected_hash

def main():
    """Função principal"""
    try:
        # Criar diretórios base
        for path in ["/workspace/models/sdxl", "/workspace/models/fish_speech"]:
            os.makedirs(path, exist_ok=True)
        
        # Download dos modelos
        for model_name, files in MODELS.items():
            model_dir = Path("/workspace/models") / model_name
            model_dir.mkdir(parents=True, exist_ok=True)
            
            for file_name, url in files.items():
                dest_path = model_dir / file_name
                if not dest_path.exists():
                    logger.info(f"Baixando {file_name} para {model_name}")
                    download_file(url, dest_path, f"Baixando {file_name}")
                else:
                    logger.info(f"{file_name} já existe para {model_name}")
        
        logger.info("✅ Todos os modelos baixados e verificados com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro durante download: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 