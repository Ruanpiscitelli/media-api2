"""
Funções de segurança para autenticação e autorização
"""
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt, jws
from src.core.config import settings
from fastapi import HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets
import logging

logger = logging.getLogger(__name__)

# Configuração do contexto de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha está correta
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Gera hash da senha
    """
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria um token JWT
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_jwt(token: str) -> dict:
    """Verifica e decodifica JWT"""
    try:
        # Verificar algoritmo explicitamente usando jose
        header = jws.get_unverified_headers(token)
        if header['alg'] != settings.ALGORITHM:
            raise HTTPException(
                status_code=401,
                detail="Invalid token algorithm"
            )
            
        # Decodificar com verificações usando jose
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Verificar claims obrigatórias
        if not all(claim in payload for claim in ['exp', 'iat', 'sub']):
            raise HTTPException(
                status_code=401, 
                detail="Missing required claims"
            )
            
        return payload
        
    except JWTError as e:
        logger.warning(f"Token inválido: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        ) 