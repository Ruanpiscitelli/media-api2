"""
Operações CRUD para modelos do banco de dados
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .models import User
from src.core.security import get_password_hash

class UserCRUD:
    """Operações CRUD para o modelo User"""
    
    def create(self, db: Session, user_data: Dict[str, Any]) -> User:
        """
        Cria um novo usuário
        """
        # Hash da senha antes de salvar
        if "password" in user_data:
            user_data["hashed_password"] = get_password_hash(user_data.pop("password"))
            
        user = User(**user_data)
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        except IntegrityError:
            db.rollback()
            raise ValueError("Usuário já existe")

    def get_by_id(self, db: Session, user_id: int) -> Optional[User]:
        """
        Busca usuário por ID
        """
        return db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, db: Session, username: str) -> Optional[User]:
        """
        Busca usuário por username
        """
        return db.query(User).filter(User.username == username).first()

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """
        Busca usuário por email
        """
        return db.query(User).filter(User.email == email).first()

    def update(self, db: Session, user_id: int, update_data: Dict[str, Any]) -> Optional[User]:
        """
        Atualiza dados do usuário
        """
        user = self.get_by_id(db, user_id)
        if not user:
            return None
            
        # Hash da senha se estiver sendo atualizada
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
            
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
                
        try:
            db.commit()
            db.refresh(user)
            return user
        except IntegrityError:
            db.rollback()
            raise ValueError("Dados inválidos para atualização")

    def delete(self, db: Session, user_id: int) -> bool:
        """
        Remove um usuário
        """
        user = self.get_by_id(db, user_id)
        if not user:
            return False
            
        try:
            db.delete(user)
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

# Instância única para uso em toda a aplicação
user_crud = UserCRUD() 