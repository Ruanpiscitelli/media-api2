"""
Rate limiting simples
"""
import logging
from fastapi import Request, HTTPException
from src.core.cache import cache
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class RateLimiter:
    """Limitador de taxa de requisições"""
    
    def __init__(self):
        self.requests: Dict[str, Tuple[int, datetime]] = {}
        self.lock = asyncio.Lock()
        
    async def __call__(self, request: Request):
        """
        Torna a classe callable para uso como dependência do FastAPI
        """
        return await self.check_rate_limit(request)
        
    async def check_rate_limit(self, request: Request) -> bool:
        """
        Verifica se o cliente excedeu o limite de requisições
        
        Args:
            request: Request do FastAPI
            
        Returns:
            True se dentro do limite, False se excedeu
            
        Raises:
            HTTPException: Se limite excedido
        """
        client_ip = request.client.host
        now = datetime.now()
        
        async with self.lock:
            if client_ip in self.requests:
                count, start_time = self.requests[client_ip]
                
                # Reseta contador se passou 1 hora
                if now - start_time > timedelta(hours=1):
                    self.requests[client_ip] = (1, now)
                    return True
                    
                # Verifica limite
                if count >= 100:  # 100 requisições por hora
                    raise HTTPException(
                        status_code=429,
                        detail="Too many requests"
                    )
                    
                # Incrementa contador
                self.requests[client_ip] = (count + 1, start_time)
            else:
                # Primeira requisição
                self.requests[client_ip] = (1, now)
                
            return True

# Instância global
rate_limiter = RateLimiter()