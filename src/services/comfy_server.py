"""
Módulo para interação com o servidor ComfyUI.
"""

import logging
from typing import Optional, Dict, Any

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

class ComfyServer:
    """Cliente para comunicação com o servidor ComfyUI"""
    
    def __init__(self):
        """Inicializa o cliente ComfyUI."""
        self.base_url = settings.COMFY_API_URL
        self.ws_url = settings.COMFY_WS_URL
        self.timeout = settings.COMFY_TIMEOUT
        self.api_key = getattr(settings, 'COMFY_API_KEY', None)  # Torna opcional
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
    
    async def get_status(self) -> Dict[str, Any]:
        """Verifica o status do servidor ComfyUI.
        
        Returns:
            Dict[str, Any]: Dicionário contendo o status do servidor e possíveis erros
            Exemplo: {"ready": True} ou {"ready": False, "error": "mensagem de erro"}
        """
        try:
            # Garante que temos uma sessão válida
            if not self.session or self.session.closed:
                self.session = await self._get_session()
            
            # Usa a URL completa para a requisição
            url = f"{self.base_url}/status"
            async with self.session.get(url, timeout=self.timeout) as response:
                if response.status != 200:
                    logger.warning(f"ComfyUI retornou status code inesperado: {response.status}")
                    return {"ready": False, "error": f"Status code inesperado: {response.status}"}
                
                try:
                    return await response.json()
                except aiohttp.ContentTypeError as e:
                    # Trata respostas não-JSON
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

# Instância global do cliente ComfyUI
comfy_server = ComfyServer() 