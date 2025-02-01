"""
Serviço de autenticação e autorização.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Optional
from src.core.config import settings
from datetime import datetime, timedelta

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Valida o token JWT e retorna o usuário atual.
    
    Args:
        token: Token JWT de autenticação
        
    Returns:
        Dict com dados do usuário
        
    Raises:
        HTTPException: Se o token for inválido
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return {"username": username}
    except JWTError:
        raise credentials_exception 

async def create_gpu_bound_token(user, gpu_id):
    """Cria token JWT vinculado a GPU específica"""
    expires = datetime.utcnow() + timedelta(minutes=30)
    payload = {
        "sub": user.username,
        "gpu_id": gpu_id,
        "exp": expires
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

async def validate_gpu_access(token, gpu_id):
    """Valida se token tem acesso à GPU solicitada"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        token_gpu = payload.get('gpu_id')
        if not token_gpu or token_gpu != gpu_id:
            raise HTTPException(status_code=403, detail="Acesso à GPU não autorizado")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {str(e)}") 