"""
Dependências centralizadas para injeção na API.
"""
from typing import AsyncGenerator
from src.services.comfy_server import get_comfy_server, ComfyServer

async def get_comfy() -> AsyncGenerator[ComfyServer, None]:
    """Dependency para injetar ComfyServer."""
    comfy = await get_comfy_server()
    try:
        yield comfy
    finally:
        await comfy.close() 