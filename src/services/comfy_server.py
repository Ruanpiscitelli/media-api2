"""
Módulo para interação com o servidor ComfyUI.
"""

import logging
from typing import Optional, Dict, Any
from src.core.config import settings  # Adicionando import correto das configurações

logger = logging.getLogger(__name__)

try:
    import aiohttp
except ImportError as e:
    logger.error(f"Erro ao importar aiohttp: {e}")
    logger.info("Tentando instalar aiohttp...")
    import subprocess
    try:
        subprocess.check_call(["pip", "install", "--no-cache-dir", "aiohttp[speedups]"])
        import aiohttp
    except Exception as install_error:
        logger.error(f"Falha ao instalar aiohttp: {install_error}")
        raise

from tenacity import retry, stop_after_attempt, wait_exponential

class ComfyServer:
    """Cliente para comunicação com o servidor ComfyUI"""
    
    def __init__(self):
        """Inicializa o cliente ComfyUI."""
        try:
            self.base_url = settings.COMFY_API_URL
            self.ws_url = settings.COMFY_WS_URL
            self.timeout = settings.COMFY_TIMEOUT
            self.api_key = getattr(settings, 'COMFY_API_KEY', None)
        except AttributeError as e:
            logger.error(f"Erro ao carregar configurações: {e}")
            # Valores padrão de fallback
            self.base_url = "http://localhost:8188"
            self.ws_url = "ws://localhost:8188"
            self.timeout = 30
            self.api_key = None
            
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Retorna uma sessão HTTP."""
        if self.session is None or self.session.closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self.session = aiohttp.ClientSession(
                headers=headers
            )
        return self.session
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_status(self) -> Dict[str, Any]:
        """Verifica o status do servidor ComfyUI com retry automático."""
        try:
            if not self.session or self.session.closed:
                self.session = await self._get_session()
            
            url = f"{self.base_url}/status"
            async with self.session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                raise_for_status=True
            ) as response:
                try:
                    return await response.json()
                except aiohttp.ContentTypeError as e:
                    text = await response.text()
                    logger.error(f"Resposta não-JSON do ComfyUI: {text}")
                    return {"ready": False, "error": "Resposta inválida do servidor"}
                
        except aiohttp.ClientError as e:
            logger.error(f"Erro de conexão com ComfyUI: {str(e)}")
            return {"ready": False, "error": f"Erro de conexão: {str(e)}"}
        except Exception as e:
            logger.error(f"Erro inesperado ao verificar status do ComfyUI: {str(e)}")
            return {"ready": False, "error": str(e)}
    
    async def close(self):
        """Fecha a sessão HTTP."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def verify_connection(self) -> bool:
        """Verifica se a conexão com o ComfyUI está funcionando."""
        try:
            status = await self.get_status()
            return status.get("ready", False)
        except Exception as e:
            logger.error(f"Falha ao verificar conexão com ComfyUI: {e}")
            return False

    @classmethod
    async def create(cls) -> 'ComfyServer':
        """Factory method para criar uma instância verificada do ComfyServer."""
        server = cls()
        if not await server.verify_connection():
            logger.warning("ComfyUI não está respondendo, usando instância offline")
        return server

async def get_comfy_server() -> ComfyServer:
    """Retorna uma instância verificada do ComfyServer."""
    return await ComfyServer.create()