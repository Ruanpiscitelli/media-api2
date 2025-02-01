"""Middleware de timeout dinâmico para requisições"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class TimeoutMiddleware(BaseHTTPMiddleware):
    # Timeouts em segundos para diferentes tipos de endpoints
    ENDPOINT_TIMEOUTS: Dict[str, int] = {
        '/video': 900,        # 15 minutos para processamento de vídeo
        '/image/generate': 600,  # 10 minutos para geração de imagens
        'default': 300        # 5 minutos para outros endpoints
    }

    def __init__(self, app):
        super().__init__(app)

    def get_timeout_for_path(self, path: str) -> int:
        """
        Determina o timeout apropriado baseado no path da requisição
        """
        for endpoint, timeout in self.ENDPOINT_TIMEOUTS.items():
            if endpoint in path:
                return timeout
        return self.ENDPOINT_TIMEOUTS['default']

    async def dispatch(self, request: Request, call_next):
        try:
            # Determina o timeout baseado no endpoint
            path = request.url.path
            timeout = self.get_timeout_for_path(path)

            # Adiciona margem de segurança de 10%
            timeout_with_margin = int(timeout * 1.1)
            
            logger.debug(f"Definido timeout de {timeout_with_margin}s para {path}")
            
            return await asyncio.wait_for(
                call_next(request),
                timeout=timeout_with_margin
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout após {timeout_with_margin}s na requisição: {path}")
            raise HTTPException(
                status_code=504,
                detail=f"Request timeout após {timeout_with_margin} segundos"
            ) 