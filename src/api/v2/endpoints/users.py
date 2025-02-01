"""
Endpoints para gerenciamento de usuários.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

from src.core.config import settings
from src.services.auth import get_current_user, get_current_admin_user
from src.services.user_manager import UserManager
from src.models.user import UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

# Schemas
class UserBase(BaseModel):
    """Dados base do usuário."""
    email: EmailStr = Field(..., description="Email do usuário")
    name: str = Field(..., description="Nome completo")
    role: UserRole = Field(default=UserRole.USER, description="Papel/função do usuário")
    is_active: bool = Field(default=True, description="Se o usuário está ativo")

class UserCreate(UserBase):
    """Dados para criar usuário."""
    password: str = Field(..., description="Senha do usuário", min_length=8)

class UserUpdate(BaseModel):
    """Dados para atualizar usuário."""
    name: Optional[str] = Field(None, description="Nome completo")
    email: Optional[EmailStr] = Field(None, description="Email do usuário")
    role: Optional[UserRole] = Field(None, description="Papel/função do usuário")
    is_active: Optional[bool] = Field(None, description="Se o usuário está ativo")
    password: Optional[str] = Field(None, description="Nova senha", min_length=8)

class UserResponse(UserBase):
    """Resposta com dados do usuário."""
    id: str = Field(..., description="ID do usuário")
    created_at: datetime = Field(..., description="Data de criação")
    updated_at: datetime = Field(..., description="Data da última atualização")
    last_login: Optional[datetime] = Field(None, description="Data do último login")
    
    class Config:
        from_attributes = True

class UserList(BaseModel):
    """Lista de usuários."""
    users: List[UserResponse] = Field(..., description="Lista de usuários")
    total: int = Field(..., description="Total de usuários")

# Endpoints
@router.get("", response_model=UserList)
async def list_users(
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    current_user = Depends(get_current_admin_user)
):
    """
    Lista usuários (apenas admin).
    Permite filtrar por role, status e busca por nome/email.
    """
    try:
        user_manager = UserManager()
        users = await user_manager.list_users(
            role=role,
            is_active=is_active,
            search=search,
            limit=limit,
            offset=offset
        )
        
        total = await user_manager.count_users(
            role=role,
            is_active=is_active,
            search=search
        )
        
        return {
            "users": users,
            "total": total
        }
        
    except Exception as e:
        logger.error(f"Erro listando usuários: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user = Depends(get_current_admin_user)
):
    """
    Cria novo usuário (apenas admin).
    """
    try:
        user_manager = UserManager()
        
        # Verificar se email já existe
        if await user_manager.get_user_by_email(user_data.email):
            raise HTTPException(
                status_code=400,
                detail="Email já cadastrado"
            )
            
        # Criar usuário
        user = await user_manager.create_user(user_data)
        return user
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro criando usuário: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """
    Obtém dados do usuário atual.
    """
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user = Depends(get_current_user)
):
    """
    Atualiza dados do usuário atual.
    """
    try:
        user_manager = UserManager()
        
        # Verificar se email já existe
        if user_data.email and user_data.email != current_user.email:
            if await user_manager.get_user_by_email(user_data.email):
                raise HTTPException(
                    status_code=400,
                    detail="Email já cadastrado"
                )
        
        # Não permitir alterar role
        if user_data.role:
            raise HTTPException(
                status_code=400,
                detail="Não é permitido alterar o próprio role"
            )
            
        # Atualizar usuário
        user = await user_manager.update_user(
            user_id=current_user.id,
            user_data=user_data
        )
        return user
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro atualizando usuário: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user = Depends(get_current_admin_user)
):
    """
    Obtém dados de um usuário específico (apenas admin).
    """
    try:
        user_manager = UserManager()
        user = await user_manager.get_user(user_id)
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="Usuário não encontrado"
            )
            
        return user
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro obtendo usuário {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user = Depends(get_current_admin_user)
):
    """
    Atualiza dados de um usuário específico (apenas admin).
    """
    try:
        user_manager = UserManager()
        
        # Verificar se usuário existe
        user = await user_manager.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="Usuário não encontrado"
            )
            
        # Verificar se email já existe
        if user_data.email and user_data.email != user.email:
            if await user_manager.get_user_by_email(user_data.email):
                raise HTTPException(
                    status_code=400,
                    detail="Email já cadastrado"
                )
                
        # Atualizar usuário
        user = await user_manager.update_user(
            user_id=user_id,
            user_data=user_data
        )
        return user
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro atualizando usuário {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user = Depends(get_current_admin_user)
):
    """
    Remove um usuário (apenas admin).
    """
    try:
        user_manager = UserManager()
        
        # Verificar se usuário existe
        user = await user_manager.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="Usuário não encontrado"
            )
            
        # Não permitir remover a si mesmo
        if user_id == current_user.id:
            raise HTTPException(
                status_code=400,
                detail="Não é permitido remover a si mesmo"
            )
            
        # Remover usuário
        await user_manager.delete_user(user_id)
        
        return {
            "status": "success",
            "message": "Usuário removido com sucesso"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro removendo usuário {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 