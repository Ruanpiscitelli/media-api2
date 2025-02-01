"""
Testes para o módulo principal da API.
"""

import os
import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import torch
import shutil

# Adicionar diretório src ao PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

# Configurar variáveis de ambiente para teste
os.environ["ENV_FILE"] = str(Path(__file__).parent / ".env.test")

# Criar diretórios necessários
test_dirs = [
    "./tests/test_data/media",
    "./tests/test_data/media/temp",
    "./tests/test_data/logs",
    "./tests/test_data/models",
    "./tests/test_data/models/lora",
    "./tests/test_data/models/checkpoints",
    "./static"
]

for dir_path in test_dirs:
    Path(dir_path).mkdir(parents=True, exist_ok=True)

from src.main import app

class TestMainAPI(unittest.TestCase):
    def setUp(self):
        """Configuração inicial para cada teste"""
        self.client = TestClient(app)
        
        # Mock das variáveis de ambiente
        self.env_patcher = patch.dict(os.environ, {
            "ENV_FILE": str(Path(__file__).parent / ".env.test"),
            "DEBUG": "true",
            "API_HOST": "0.0.0.0",
            "API_PORT": "8000",
            "API_WORKERS": "4",
            "CORS_ORIGINS": '["http://localhost:3000","http://localhost:8000"]',
            "SECRET_KEY": "test-secret-key",
            "CUDA_VISIBLE_DEVICES": "0",
            "MEDIA_DIR": "./tests/test_data/media",
            "TEMP_DIR": "./tests/test_data/media/temp",
            "LOG_DIR": "./tests/test_data/logs",
            "MODELS_DIR": "./tests/test_data/models",
            "LORA_DIR": "./tests/test_data/models/lora",
            "CHECKPOINTS_DIR": "./tests/test_data/models/checkpoints"
        })
        self.env_patcher.start()
    
    def tearDown(self):
        """Limpeza após cada teste"""
        self.env_patcher.stop()
        
        # Limpar diretórios de teste
        for dir_path in test_dirs:
            if Path(dir_path).exists():
                shutil.rmtree(dir_path)
    
    def test_health_check_healthy(self):
        """Testa o endpoint de health check quando o sistema está saudável"""
        async def mock_get_status():
            return {"ready": True}
        
        with patch("src.services.comfy_server.comfy_server.get_status", new=AsyncMock(side_effect=mock_get_status)), \
             patch("torch.cuda.is_available", return_value=True):
            response = self.client.get("/health")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "healthy")
            self.assertEqual(data["services"]["gpu"], "available")
    
    def test_health_check_unhealthy(self):
        """Testa o endpoint de health check quando há problemas"""
        async def mock_get_status():
            return {"ready": True}
        
        with patch("src.services.comfy_server.comfy_server.get_status", new=AsyncMock(side_effect=mock_get_status)), \
             patch("torch.cuda.is_available", return_value=False):
            response = self.client.get("/health")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "healthy")
            self.assertEqual(data["services"]["gpu"], "unavailable")
    
    def test_health_check_comfy_error(self):
        """Testa o endpoint de health check quando o ComfyUI não está pronto"""
        async def mock_get_status():
            return {"ready": False}
        
        with patch("src.services.comfy_server.comfy_server.get_status", new=AsyncMock(side_effect=mock_get_status)):
            print("\nTestando health check com ComfyUI não pronto")
            response = self.client.get("/health")
            print("Response status:", response.status_code)
            print("Response body:", response.json())
            self.assertEqual(response.status_code, 503)
            data = response.json()
            self.assertEqual(data["status"], "unhealthy")
            self.assertIn("ComfyUI", data["error"])
    
    def test_gpu_timeout_middleware(self):
        """Testa o middleware de timeout para operações GPU"""
        # Mock de uma operação que excede o timeout
        async def mock_long_operation():
            import asyncio
            await asyncio.sleep(2)
            return {"status": "ok"}

        app.get("/api/v2/processing/test")(mock_long_operation)
        
        with patch.dict(os.environ, {"RENDER_TIMEOUT_SECONDS": "1"}):
            response = self.client.get("/api/v2/processing/test")
            self.assertEqual(response.status_code, 504)
            data = response.json()
            self.assertIn("timeout", data["detail"].lower())
    
    def test_cors_middleware(self):
        """Testa a configuração do CORS"""
        # Testar origem permitida
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type"
        }
        print("\nOrigins permitidas:", os.environ.get("CORS_ORIGINS"))
        print("Headers:", headers)
        response = self.client.options(
            "/health",
            headers=headers
        )
        print("Response status:", response.status_code)
        print("Response headers:", response.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:3000"
        )
        self.assertEqual(
            response.headers["access-control-allow-methods"],
            "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        )
        
        # Testar origem não permitida
        headers["Origin"] = "http://malicious.com"
        response = self.client.options(
            "/health",
            headers=headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("access-control-allow-origin", response.headers)
    
    def test_static_files(self):
        """Testa o acesso a arquivos estáticos"""
        # Criar diretório e arquivo de teste
        test_dir = Path("static")
        test_dir.mkdir(exist_ok=True)
        test_file = test_dir / "test.txt"
        test_file.write_text("test content")
        
        try:
            response = self.client.get("/static/test.txt")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.text, "test content")
        finally:
            # Limpar arquivo de teste
            if test_file.exists():
                test_file.unlink()
    
    def test_api_documentation(self):
        """Testa a documentação da API"""
        response = self.client.get("/docs")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["info"]["title"], "Media Generation API")
        self.assertEqual(data["info"]["version"], "2.0.0")

if __name__ == "__main__":
    unittest.main(verbosity=2) 