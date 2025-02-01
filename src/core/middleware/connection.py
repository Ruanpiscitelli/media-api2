"""
Middleware para gerenciamento de conexões
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio
from src.core.config import settings

class ConnectionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._semaphore = asyncio.Semaphore(settings.MAX_CONNECTIONS)
        
    async def dispatch(self, request: Request, call_next):
        async with self._semaphore:
            return await call_next(request) 