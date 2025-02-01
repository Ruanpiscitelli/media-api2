"""
Middleware para controle de timeout das requisições
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)

class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            # Ajustar timeout baseado no endpoint
            path = request.url.path
            timeout = (
                settings.LONG_TIMEOUT 
                if any(p in path for p in ['/video', '/image/generate'])
                else settings.REQUEST_TIMEOUT
            )

            # Adicionar margem de segurança
            timeout = int(timeout * 1.1)
            
            return await asyncio.wait_for(
                call_next(request),
                timeout=timeout
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout na requisição: {request.url}")
            raise HTTPException(
                status_code=504,
                detail="Request timeout"
            ) 