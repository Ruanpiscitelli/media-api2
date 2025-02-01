"""
Pure ASGI Middleware para melhor performance
"""
from typing import Awaitable, Callable
from starlette.types import ASGIApp, Receive, Scope, Send

class PureASGIRateLimiter:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Implementar rate limiting aqui
        await self.app(scope, receive, send)

# Usar no main.py:
# app.add_middleware(PureASGIRateLimiter) 