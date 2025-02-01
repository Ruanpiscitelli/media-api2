"""
Script de inicialização que gerencia o setup e inicialização do servidor.
"""

import asyncio
import logging
import sys
from pathlib import Path
import json
import subprocess
import os
import signal
from typing import Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServerManager:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent.parent
        self.first_run_flag = self.base_path / ".first_run"
        self.comfy_process: Optional[subprocess.Popen] = None
        self.server_process: Optional[subprocess.Popen] = None
    
    def is_first_run(self) -> bool:
        """Verifica se é a primeira execução"""
        return not self.first_run_flag.exists()
    
    async def setup_environment(self):
        """Configura o ambiente na primeira execução"""
        logger.info("🚀 Configurando ambiente pela primeira vez...")
        
        try:
            # Importar scripts de setup
            sys.path.append(str(self.base_path / "src"))
            from scripts.download_models import ModelDownloader
            from scripts.setup_comfy import ComfyUISetup
            
            # Baixar modelos
            logger.info("📥 Baixando modelos...")
            downloader = ModelDownloader()
            downloader.download_models()
            downloader.save_model_info()
            
            # Configurar ComfyUI
            logger.info("⚙️ Configurando ComfyUI...")
            setup = ComfyUISetup()
            setup.setup()
            
            # Criar flag de primeira execução
            self.first_run_flag.touch()
            logger.info("✅ Setup inicial concluído com sucesso!")
            
        except Exception as e:
            logger.error(f"❌ Erro no setup inicial: {str(e)}")
            sys.exit(1)
    
    def start_comfy(self):
        """Inicia o servidor ComfyUI"""
        logger.info("🚀 Iniciando ComfyUI...")
        
        try:
            self.comfy_process = subprocess.Popen(
                [sys.executable, "src/scripts/start_comfy.py"],
                cwd=str(self.base_path)
            )
            logger.info("✅ ComfyUI iniciado!")
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar ComfyUI: {str(e)}")
            sys.exit(1)
    
    def start_main_server(self):
        """Inicia o servidor principal"""
        logger.info("🚀 Iniciando servidor principal...")
        
        try:
            self.server_process = subprocess.Popen(
                [
                    sys.executable, "-m", "uvicorn",
                    "src.api.main:app",
                    "--host", "0.0.0.0",
                    "--port", "8000",
                    "--reload"
                ],
                cwd=str(self.base_path)
            )
            logger.info("✅ Servidor principal iniciado!")
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar servidor principal: {str(e)}")
            sys.exit(1)
    
    def stop_servers(self, signum=None, frame=None):
        """Para todos os servidores graciosamente"""
        logger.info("🛑 Parando servidores...")
        
        if self.comfy_process:
            self.comfy_process.terminate()
            self.comfy_process.wait()
            logger.info("✅ ComfyUI finalizado")
        
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            logger.info("✅ Servidor principal finalizado")
        
        sys.exit(0)
    
    async def run(self):
        """Executa todo o processo de inicialização"""
        # Registrar handler para SIGINT/SIGTERM
        signal.signal(signal.SIGINT, self.stop_servers)
        signal.signal(signal.SIGTERM, self.stop_servers)
        
        try:
            # Verificar primeira execução
            if self.is_first_run():
                await self.setup_environment()
            
            # Iniciar servidores
            self.start_comfy()
            self.start_main_server()
            
            # Manter script rodando
            while True:
                # Verificar se processos ainda estão rodando
                if self.comfy_process.poll() is not None:
                    logger.error("❌ ComfyUI parou inesperadamente!")
                    self.stop_servers()
                
                if self.server_process.poll() is not None:
                    logger.error("❌ Servidor principal parou inesperadamente!")
                    self.stop_servers()
                
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Erro fatal: {str(e)}")
            self.stop_servers()

def main():
    """Função principal"""
    try:
        manager = ServerManager()
        asyncio.run(manager.run())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main() 