"""
Schemas Pydantic para autenticação e usuários.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator

class TokenResponse(BaseModel):
    """Schema para resposta de token."""
    access_token: str
    token_type: str
    expires_in: int

class UserBase(BaseModel):
    """Schema base para usuário."""
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    tier: str = Field(default="free", regex="^(free|pro|enterprise)$")

class UserCreate(UserBase):
    """Schema para criação de usuário."""
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        """Valida complexidade da senha."""
        if not any(c.isupper() for c in v):
            raise ValueError('Senha deve conter pelo menos uma letra maiúscula')
        if not any(c.islower() for c in v):
            raise ValueError('Senha deve conter pelo menos uma letra minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('Senha deve conter pelo menos um número')
        return v

class UserUpdate(BaseModel):
    """Schema para atualização de usuário."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        """Valida complexidade da senha."""
        if v is None:
            return v
        if not any(c.isupper() for c in v):
            raise ValueError('Senha deve conter pelo menos uma letra maiúscula')
        if not any(c.islower() for c in v):
            raise ValueError('Senha deve conter pelo menos uma letra minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('Senha deve conter pelo menos um número')
        return v

class UserResponse(UserBase):
    """Schema para resposta de usuário."""
    id: str
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class UserInDB(UserBase):
    """Schema para usuário no banco de dados."""
    id: str
    hashed_password: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    is_verified: bool = False
    
    class Config:
        orm_mode = True

class TokenData(BaseModel):
    """Schema para dados do token JWT."""
    sub: str
    tier: str = Field(default="free", regex="^(free|pro|enterprise)$")
    exp: datetime 