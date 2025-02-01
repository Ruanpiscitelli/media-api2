"""
Módulo para interação com o servidor ComfyUI.
"""

import aiohttp
import logging
from src.core.config import settings

logger = logging.getLogger(__name__)

class ComfyServer:
    """Cliente para interação com o servidor ComfyUI."""
    
    def __init__(self):
        """Inicializa o cliente ComfyUI."""
        self.base_url = settings.COMFY_API_URL
        self.ws_url = settings.COMFY_WS_URL
        self.timeout = settings.COMFY_TIMEOUT
        self.api_key = getattr(settings, 'COMFY_API_KEY', None)  # Torna opcional
        self.session = None
    
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
    
    async def get_status(self) -> dict:
        """Verifica o status do servidor ComfyUI."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/status") as response:
                if response.status == 200:
                    return {"ready": True}
                return {"ready": False}
        except Exception as e:
            logger.error(f"Erro ao verificar status do ComfyUI: {e}")
            return {"ready": False}
    
    async def close(self):
        """Fecha a sessão HTTP."""
        if self.session and not self.session.closed:
            await self.session.close()

# Instância global do cliente ComfyUI
comfy_server = ComfyServer() 