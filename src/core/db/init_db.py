"""
Script para inicialização do banco de dados
"""
from .database import engine, Base
from .models import User

def init_db():
    Base.metadata.create_all(bind=engine) 