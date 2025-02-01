"""
Inicialização do banco de dados e exportação das dependências
"""
from .models import User
from .database import get_db, Base, engine

# Exporta engine para ser importado de src.core.db
__all__ = ['engine'] 