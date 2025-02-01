"""
Script para inicialização do banco de dados
"""
from .database import engine, Base
from .models import User

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) 