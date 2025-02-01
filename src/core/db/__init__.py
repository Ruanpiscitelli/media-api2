"""
Inicialização do banco de dados e exportação das dependências
"""
from .database import (
    engine,
    async_engine,
    Base,
    get_db,
    get_async_db,
    AsyncSessionLocal,
    SessionLocal
)

# Exporta as dependências necessárias
__all__ = [
    'engine',
    'async_engine', 
    'Base',
    'get_db',
    'get_async_db',
    'AsyncSessionLocal',
    'SessionLocal'
] 