"""
Módulo central de autenticação.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import time
from typing import Optional
from src.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Valida o token JWT e retorna o usuário atual.
    
    Args:
        token: Token JWT de autenticação
        
    Returns:
        dict: Dicionário contendo apenas o ID do usuário na chave 'sub'
        
    Raises:
        HTTPException: Se o token for inválido
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verificar se token não expirou
        payload = jwt.decode(
            token, 
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        exp = payload.get("exp")
        if not exp or float(exp) < time.time():
            raise credentials_exception
            
        # Verificar se usuário ainda existe/está ativo
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
            
        # Verificar se token não está na blacklist
        redis = await get_redis_client()
        if await redis.sismember("token_blacklist", token):
            raise credentials_exception
            
        # Retorna apenas o dicionário com a chave 'sub' para manter compatibilidade
        return {"sub": user_id}
        
    except JWTError:
        raise credentials_exception 