"""
Middleware de autenticação JWT.
Valida tokens e gerencia permissões de acesso.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.core.config import settings
from src.core.cache.manager import cache_manager


class AuthJWTMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.security = HTTPBearer()
        self.cache = cache_manager.get_cache("auth")
        
    async def dispatch(self, request: Request, call_next):
        # Rotas públicas que não precisam de autenticação
        if self._is_public_route(request.url.path):
            return await call_next(request)
            
        try:
            # Extrai e valida o token
            auth: HTTPAuthorizationCredentials = await self.security(request)
            token_data = self._verify_jwt_token(auth.credentials)
            
            # Verifica se o token está na blacklist
            if await self._is_token_blacklisted(auth.credentials):
                raise HTTPException(status_code=401, detail="Token inválido ou expirado")
            
            # Adiciona informações do usuário ao request state
            request.state.user = token_data
            
            # Verifica permissões específicas da rota
            if not self._check_route_permissions(request, token_data):
                raise HTTPException(status_code=403, detail="Acesso não autorizado")
            
            return await call_next(request)
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"detail": "Erro interno de autenticação"}
            )
    
    def _is_public_route(self, path: str) -> bool:
        """Verifica se a rota é pública."""
        public_routes = [
            "/health",
            "/docs",
            "/openapi.json",
            "/v2/auth/login",
            "/v2/auth/register"
        ]
        return any(path.startswith(route) for route in public_routes)
    
    def _verify_jwt_token(self, token: str) -> dict:
        """Verifica e decodifica o token JWT."""
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=401,
                detail="Token inválido ou expirado"
            )
    
    async def _is_token_blacklisted(self, token: str) -> bool:
        """Verifica se o token está na blacklist."""
        return await self.cache.exists(f"blacklist:{token}")
    
    def _check_route_permissions(self, request: Request, token_data: dict) -> bool:
        """Verifica permissões específicas da rota."""
        # Implementar lógica de permissões baseada em roles
        return True
    
    @staticmethod
    def create_access_token(
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Cria um novo token JWT."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
            
        to_encode.update({"exp": expire})
        
        return jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        ) 