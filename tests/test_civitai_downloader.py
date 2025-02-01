"""
Testes para o módulo de download do Civitai.
"""

import os
import sys
import unittest
from pathlib import Path
import shutil
import json
import requests
from unittest.mock import patch, MagicMock

# Adicionar diretório src ao PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent / "src"))

from scripts.download_civitai import CivitaiDownloader

class TestCivitaiDownloader(unittest.TestCase):
    def setUp(self):
        """Configuração inicial para cada teste"""
        self.test_dir = Path(__file__).parent / "test_data"
        self.test_dir.mkdir(exist_ok=True)
        
        # Mock das variáveis de ambiente
        self.env_patcher = patch.dict(os.environ, {
            "CIVITAI_API_KEY": "test_key",
            "MODELS_DIR": str(self.test_dir / "models")
        })
        self.env_patcher.start()
        
        # Instanciar downloader
        self.downloader = CivitaiDownloader()
        self.downloader.base_path = self.test_dir
        self.downloader.models_path = self.test_dir / "models"
        self.downloader.checkpoints_path = self.downloader.models_path / "checkpoints"
        self.downloader.lora_path = self.downloader.models_path / "lora"
        
        # Criar diretórios necessários
        self.downloader.models_path.mkdir(parents=True, exist_ok=True)
        self.downloader.checkpoints_path.mkdir(parents=True, exist_ok=True)
        self.downloader.lora_path.mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """Limpeza após cada teste"""
        self.env_patcher.stop()
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_init(self):
        """Testa a inicialização do downloader"""
        self.assertEqual(self.downloader.api_key, "test_key")
        self.assertEqual(
            self.downloader.headers["Authorization"],
            "Bearer test_key"
        )
    
    def test_create_directories(self):
        """Testa a criação dos diretórios necessários"""
        # Remover diretórios para testar criação
        shutil.rmtree(self.downloader.models_path)
        
        # Criar diretórios sem fazer download
        self.downloader.checkpoints_path.mkdir(parents=True, exist_ok=True)
        self.downloader.lora_path.mkdir(parents=True, exist_ok=True)
        
        self.assertTrue(self.downloader.checkpoints_path.exists())
        self.assertTrue(self.downloader.lora_path.exists())
    
    @patch("requests.get")
    def test_download_file(self, mock_get):
        """Testa o download de um arquivo"""
        # Mock da resposta do requests
        mock_response = MagicMock()
        mock_response.headers = {
            "content-length": "1024",
            "Content-Disposition": 'filename="test_model.safetensors"'
        }
        mock_response.iter_content.return_value = [b"test" * 256]
        mock_get.return_value = mock_response
        
        # Testar download
        dest_path = self.test_dir / "test_model.safetensors"
        success = self.downloader.download_file(
            "https://test.com/model",
            dest_path,
            "Test Model"
        )
        
        self.assertTrue(success)
        self.assertTrue(dest_path.exists())
        self.assertTrue(dest_path.stat().st_size > 0)
    
    @patch("requests.get")
    def test_download_models(self, mock_get):
        """Testa o download de todos os modelos"""
        # Mock da resposta do requests
        mock_response = MagicMock()
        mock_response.headers = {
            "content-length": "1024",
            "Content-Disposition": 'filename="test_model.safetensors"'
        }
        mock_response.iter_content.return_value = [b"test" * 256]
        mock_get.return_value = mock_response
        
        # Testar download dos modelos
        self.downloader.download_models()
        
        # Verificar se os arquivos foram criados
        for model in self.downloader.models.values():
            model_path = self.downloader.models_path / model["path"]
            model_dir = model_path.parent
            test_file = model_dir / "test_model.safetensors"
            self.assertTrue(
                test_file.exists(),
                f"Modelo {model['name']} não foi baixado"
            )
    
    def test_save_model_info(self):
        """Testa o salvamento das informações dos modelos"""
        self.downloader.save_model_info()
        
        info_path = self.downloader.models_path / "civitai_models_info.json"
        self.assertTrue(info_path.exists())
        
        # Verificar conteúdo do arquivo
        with open(info_path) as f:
            info = json.load(f)
        
        self.assertEqual(
            len(info),
            len(self.downloader.models),
            "Número incorreto de modelos no arquivo de informações"
        )
    
    def test_error_handling(self):
        """Testa o tratamento de erros"""
        # Testar download com URL inválida
        dest_path = self.test_dir / "invalid.safetensors"
        success = self.downloader.download_file(
            "https://invalid.url",
            dest_path,
            "Invalid Model"
        )
        
        self.assertFalse(success)
        self.assertFalse(dest_path.exists())
    
    @patch("requests.head")
    def test_model_urls(self, mock_head):
        """Testa se as URLs dos modelos são válidas"""
        # Mock da resposta do requests.head
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        for model_id, model in self.downloader.models.items():
            response = requests.head(model["url"])
            self.assertEqual(
                response.status_code,
                200,
                f"URL inválida para o modelo {model_id}"
            )

if __name__ == "__main__":
    unittest.main(verbosity=2) 