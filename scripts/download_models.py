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
        "base": {
            "url": "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned.safetensors",
            "path": "/workspace/models/fish_speech/model.pt",
            "sha256": "cc6cb27103417325ff94f52b7a5d2dde45a7515b25c255d8e396c90014281516"
        }
    }
}

def download_file(url: str, dest_path: str, desc: str = None):
    """Download arquivo com barra de progresso"""
    response = requests.get(url, stream=True)
    total = int(response.headers.get('content-length', 0))
    
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
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
        for model_type, variants in MODELS.items():
            for variant_name, info in variants.items():
                dest_path = info["path"]
                
                if not os.path.exists(dest_path):
                    logger.info(f"Baixando {model_type} {variant_name}...")
                    download_file(
                        info["url"], 
                        dest_path,
                        f"Downloading {model_type} {variant_name}"
                    )
                    
                    if verify_sha256(dest_path, info["sha256"]):
                        logger.info(f"✅ {model_type} {variant_name} verificado com sucesso")
                    else:
                        logger.error(f"❌ Falha na verificação de {model_type} {variant_name}")
                        os.remove(dest_path)
                        sys.exit(1)
                else:
                    logger.info(f"Modelo {model_type} {variant_name} já existe")
        
        logger.info("✅ Todos os modelos baixados e verificados com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro durante download: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 