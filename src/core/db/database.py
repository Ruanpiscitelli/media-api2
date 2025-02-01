"""Configuração do banco de dados"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from src.core.config import settings
import os

# Configuração das URLs
if settings.ENVIRONMENT == "development":
    # SQLite
    SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
    ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./sql_app.db"
    connect_args = {"check_same_thread": False}
else:
    # PostgreSQL
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL.replace(
        'postgresql://',
        'postgresql+psycopg2://',
        1
    )
    ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
        'postgresql://',
        'postgresql+asyncpg://',
        1
    )
    connect_args = {}

# Engine síncrono
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=settings.DB_DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    connect_args=connect_args
)

# Engine assíncrono
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.DB_DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=3600
)

# Sessões
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

AsyncSessionLocal = sessionmaker(
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    bind=async_engine
)

# Base para modelos
Base = declarative_base()

# Geradores de sessão
def get_db():
    """Retorna sessão síncrona"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    """Retorna sessão assíncrona"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()