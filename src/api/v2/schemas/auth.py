"""
Schemas Pydantic para autenticação e usuários.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class TokenResponse(BaseModel):
    """Schema para resposta de token."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class UserBase(BaseModel):
    """Schema base para usuário."""
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    is_active: bool = True
    tier: str = Field(
        default="free",
        pattern="^(free|pro|enterprise)$"
    )

class UserCreate(UserBase):
    """Schema para criação de usuário."""
    password: str = Field(min_length=8)
    
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
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    tier: Optional[str] = Field(
        None,
        pattern="^(free|pro|enterprise)$"
    )
    
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
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

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
    username: Optional[str] = None
    exp: Optional[datetime] = None 