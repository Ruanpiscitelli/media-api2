"""
Script para baixar modelos e LoRAs do Civitai.
"""

import os
import sys
from pathlib import Path
import requests
from tqdm import tqdm
import logging
import json
import time
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CivitaiDownloader:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent.parent
        self.models_path = self.base_path / "models"
        self.checkpoints_path = self.models_path / "checkpoints"
        self.lora_path = self.models_path / "lora"
        
        # Configurações do Civitai
        self.api_key = os.getenv("CIVITAI_API_KEY")
        if not self.api_key:
            raise ValueError("CIVITAI_API_KEY não definida no arquivo .env")
        
        # Headers para requisições
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Modelos para download
        self.models = {
            "colossus_xl": {
                "name": "Colossus Project XL",
                "url": "https://civitai.com/api/download/models/1261969?type=Model&format=SafeTensor&size=full&fp=fp8",
                "path": "checkpoints/colossus_xl.safetensors",
                "type": "checkpoint"
            },
            "juggernaut_xl": {
                "name": "Juggernaut Cinematic XL",
                "url": "https://civitai.com/api/download/models/133005",
                "path": "lora/juggernaut_xl.safetensors",
                "type": "lora"
            }
        }
    
    def download_file(self, url: str, dest_path: Path, desc: str = None) -> bool:
        """
        Baixa um arquivo com barra de progresso.
        
        Args:
            url: URL do arquivo
            dest_path: Caminho de destino
            desc: Descrição para a barra de progresso
            
        Returns:
            bool indicando sucesso
        """
        try:
            response = requests.get(url, stream=True, headers=self.headers)
            response.raise_for_status()
            
            # Extrair nome do arquivo do header Content-Disposition se disponível
            if "Content-Disposition" in response.headers:
                content_disposition = response.headers["Content-Disposition"]
                if "filename=" in content_disposition:
                    filename = content_disposition.split("filename=")[1].strip('"')
                    dest_path = dest_path.parent / filename
            
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
    
    def download_models(self):
        """Baixa todos os modelos configurados"""
        logger.info("🚀 Iniciando download dos modelos do Civitai")
        
        # Criar diretórios
        self.checkpoints_path.mkdir(parents=True, exist_ok=True)
        self.lora_path.mkdir(parents=True, exist_ok=True)
        
        # Baixar modelos
        for model_id, model in self.models.items():
            model_path = self.models_path / model["path"]
            
            if model_path.exists():
                logger.info(f"✅ {model['name']} já existe")
                continue
            
            logger.info(f"Baixando {model['name']}...")
            if self.download_file(model["url"], model_path, model["name"]):
                logger.info(f"✅ {model['name']} baixado com sucesso")
            else:
                logger.error(f"❌ Erro ao baixar {model['name']}")
            
            # Aguardar um pouco entre downloads para evitar rate limiting
            time.sleep(1)
    
    def save_model_info(self):
        """Salva informações dos modelos em JSON"""
        info_path = self.models_path / "civitai_models_info.json"
        
        model_info = {
            model_id: {
                "name": model["name"],
                "path": str(self.models_path / model["path"]),
                "type": model["type"]
            }
            for model_id, model in self.models.items()
        }
        
        with open(info_path, "w") as f:
            json.dump(model_info, f, indent=4)
        
        logger.info(f"✅ Informações dos modelos salvas em {info_path}")

def main():
    try:
        downloader = CivitaiDownloader()
        
        # Baixar modelos
        downloader.download_models()
        downloader.save_model_info()
        
        logger.info("✨ Download dos modelos concluído com sucesso")
    except Exception as e:
        logger.error(f"❌ Erro fatal: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 