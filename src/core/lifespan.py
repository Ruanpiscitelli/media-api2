"""
Gerenciamento do ciclo de vida da aplicação
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio
from typing import AsyncIterator

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Gerencia ciclo de vida da aplicação de forma otimizada
    """
    # Startup
    try:
        # Inicializar recursos em paralelo
        await asyncio.gather(
            init_redis(),
            init_db(),
            init_directories(),
            init_monitoring()
        )
        yield
    finally:
        # Shutdown
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True) 