"""Configuração do banco de dados"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from src.core.config import settings
import os

# Usar SQLite para desenvolvimento
if settings.ENVIRONMENT == "development":
    SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    # SQLite não suporta async, então usamos aiosqlite
    ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./sql_app.db"
else:
    # PostgreSQL para produção
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL.replace(
        'postgresql://',
        'postgresql+psycopg2://',
        1
    )
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=settings.DB_DEBUG,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT
    )
    # Para PostgreSQL async, usamos asyncpg
    ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
        'postgresql://',
        'postgresql+asyncpg://',
        1
    )

# Criar sessão
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()

# Função para obter sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Cria engine assíncrono do SQLAlchemy
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.DB_DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=3600
)