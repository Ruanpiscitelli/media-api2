"""
Inicialização do banco de dados.
"""
import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.core.config import settings

logger = logging.getLogger(__name__)

def init_db():
    """Inicializa banco de dados"""
    try:
        # Criar diretório do banco se não existir
        db_path = Path(settings.DATABASE_URL.replace("sqlite:///", "")).parent
        db_path.mkdir(parents=True, exist_ok=True)
        
        # Criar engine
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False} 
            if settings.DATABASE_URL.startswith("sqlite") 
            else {}
        )
        
        # Criar tabelas
        from src.models import Base
        Base.metadata.create_all(bind=engine)
        
        logger.info("Banco de dados inicializado com sucesso")
        
    except Exception as e:
        logger.error(f"Erro inicializando banco de dados: {e}")
        raise 