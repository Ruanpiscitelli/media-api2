"""
Configuração do banco de dados SQLAlchemy
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool

from src.core.config import settings

# Modificar a URL do SQLite para usar o driver assíncrono
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL.replace(
    'sqlite:///', 
    'sqlite+aiosqlite:///'
)

# Criar engine com configurações assíncronas
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=AsyncAdaptedQueuePool,
    pool_pre_ping=True,
    echo=settings.SQL_DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)

# Configurar sessão assíncrona
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Função para obter sessão do banco
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close() 