"""
Endpoints de autenticação e gerenciamento de usuários.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
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

# Configuração de logging
logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/v2/auth", tags=["auth"])

# Cache
auth_cache = cache_manager.get_cache("auth")

auth_service = AuthService()

class LoginRequest(BaseModel):
    """Modelo para requisição de login"""
    username: str
    password: str

class RegisterRequest(BaseModel):
    """Modelo para requisição de registro"""
    username: str
    email: EmailStr
    password: str
    plan: str = "free"

@router.post("/login")
async def login(request: LoginRequest):
    """Login de usuário"""
    try:
        token = await auth_service.login(
            request.username,
            request.password
        )
        return {"token": token}
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/register")
async def register(request: RegisterRequest):
    """Registro de novo usuário"""
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

@router.put("/me/plan")
async def update_plan(
    plan: str,
    current_user = Depends(get_current_user)
):
    """Atualiza plano do usuário"""
    try:
        updated_user = await auth_service.update_plan(
            current_user.id,
            plan
        )
        return updated_user
    except PlanError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/refresh")
async def refresh_token(current_user = Depends(get_current_user)):
    """Atualiza o token de acesso"""
    try:
        new_token = await auth_service.refresh_token(current_user.id)
        return {"token": new_token}
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/logout")
async def logout(current_user = Depends(get_current_user)):
    """Realiza logout do usuário"""
    try:
        await auth_service.logout(current_user.id)
        return {"message": "Logout realizado com sucesso"}
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
    user: User = Depends(AuthJWTMiddleware.get_current_user)
):
    """
    Atualiza informações do usuário atual.
    """
    try:
        updated_user = await user_crud.update(user.id, user_data.dict())
        return updated_user
        
    except Exception as e:
        logger.error(f"Erro atualizando usuário: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno atualizando usuário"
        ) 