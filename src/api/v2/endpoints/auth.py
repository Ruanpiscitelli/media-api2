"""
Endpoints para autenticação e gerenciamento de usuários.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Body
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.cache.manager import cache_manager
from src.core.db.models import User
from src.core.db.crud import user_crud
from src.api.v2.middleware.auth import AuthJWTMiddleware
from src.api.v2.schemas.auth import (
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate
)
from src.core.auth import get_current_user, AuthService
from src.core.exceptions import AuthError, UserExistsError, PlanError
from src.core.db.database import get_db
from src.core.cache.redis import redis_client

# Configuração de logging
logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/auth", tags=["Autenticação"])

# Cache
auth_cache = cache_manager.get_cache("auth")

auth_service = AuthService()

class LoginRequest(BaseModel):
    """
    Modelo para requisição de login.
    
    Attributes:
        username: Nome de usuário
        password: Senha do usuário
    """
    username: str = Field(..., description="Nome de usuário")
    password: str = Field(..., description="Senha do usuário")

class RegisterRequest(BaseModel):
    """Modelo para requisição de registro"""
    username: str
    email: EmailStr
    password: str
    plan: str = "free"

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login de Usuário",
    description="""
    Realiza autenticação do usuário e retorna token JWT.
    O token deve ser usado em todas as requisições subsequentes.
    """,
    responses={
        200: {
            "description": "Login realizado com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                        "token_type": "bearer",
                        "expires_in": 3600
                    }
                }
            }
        },
        401: {
            "description": "Credenciais inválidas",
            "content": {
                "application/json": {
                    "example": {"detail": "Username ou senha incorretos"}
                }
            }
        }
    }
)
async def login(request: LoginRequest):
    """Realiza login do usuário."""
    try:
        token = await auth_service.login(
            request.username,
            request.password
        )
        
        # Cache token
        await redis_client.setex(
            f"token:{token}",
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "valid"
        )
        
        return {"token": token}
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post(
    "/register",
    response_model=TokenResponse,
    summary="Registro de Usuário",
    description="""
    Registra um novo usuário no sistema.
    Após registro bem sucedido, retorna token JWT para uso imediato.
    """,
    responses={
        200: {
            "description": "Usuário registrado com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                        "token_type": "bearer",
                        "expires_in": 3600
                    }
                }
            }
        },
        400: {
            "description": "Dados inválidos",
            "content": {
                "application/json": {
                    "example": {"detail": "Username já existe"}
                }
            }
        }
    }
)
async def register(request: RegisterRequest):
    """Registra novo usuário."""
    try:
        user = await auth_service.register(
            username=request.username,
            email=request.email,
            password=request.password,
            plan=request.plan
        )
        return {
            "message": "Usuário registrado com sucesso",
            "user_id": user.id
        }
    except UserExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/me", response_model=UserResponse)
async def get_user(current_user = Depends(get_current_user)):
    """Obtém informações do usuário atual"""
    return current_user

@router.put(
    "/me/plan",
    summary="Atualizar Plano",
    description="Atualiza o plano do usuário atual.",
    responses={
        200: {
            "description": "Plano atualizado com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": "user_123",
                        "plan": "premium",
                        "updated_at": "2024-01-30T12:00:00Z"
                    }
                }
            }
        }
    }
)
async def update_plan(
    plan: str = Body(..., description="Novo plano (free/premium)"),
    current_user = Depends(get_current_user)
):
    """Atualiza plano do usuário."""
    try:
        updated_user = await auth_service.update_plan(
            current_user.id,
            plan
        )
        return updated_user
    except PlanError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar Token",
    description="Renova o token JWT atual retornando um novo token válido.",
    responses={
        200: {
            "description": "Token renovado com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                        "token_type": "bearer",
                        "expires_in": 3600
                    }
                }
            }
        },
        401: {
            "description": "Token inválido ou expirado",
            "content": {
                "application/json": {
                    "example": {"detail": "Token inválido"}
                }
            }
        }
    }
)
async def refresh_token(current_user = Depends(get_current_user)):
    """Renova o token JWT."""
    try:
        new_token = await auth_service.refresh_token(current_user.id)
        return {"token": new_token}
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/logout")
async def logout(current_user = Depends(get_current_user)):
    """Realiza logout do usuário"""
    try:
        # Adicionar token à blacklist
        token = request.headers["Authorization"].split()[1]
        await redis_client.setex(
            f"blacklist:{token}",
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "revoked"
        )
        return {"message": "Logout successful"}
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.put("/me/password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user = Depends(get_current_user)
):
    """Altera a senha do usuário"""
    try:
        await auth_service.change_password(
            user_id=current_user.id,
            old_password=old_password,
            new_password=new_password
        )
        return {"message": "Senha alterada com sucesso"}
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.put("/me", response_model=UserResponse)
async def update_user(
    user_data: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Atualiza informações do usuário atual.
    """
    try:
        updated_user = await user_crud.update(current_user.id, user_data.dict())
        return updated_user
        
    except Exception as e:
        logger.error(f"Erro atualizando usuário: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno atualizando usuário"
        ) 