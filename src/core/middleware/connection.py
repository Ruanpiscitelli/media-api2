"""
Middleware para gerenciamento de conexões
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
from src.core.monitoring import REQUEST_LATENCY, REQUESTS, ERRORS
import logging

logger = logging.getLogger(__name__)

class ConnectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware para monitorar conexões e métricas
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Processa a requisição e coleta métricas
        
        Args:
            request: Requisição FastAPI
            call_next: Próximo handler
            
        Returns:
            Response: Resposta processada
        """
        start_time = time.time()
        method = request.method
        path = request.url.path
        
        try:
            # Processa a requisição
            response = await call_next(request)
            
            # Registra métricas de sucesso
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=path
            ).observe(time.time() - start_time)
            
            REQUESTS.labels(
                method=method,
                endpoint=path,
                status=response.status_code
            ).inc()
            
            return response
            
        except Exception as e:
            # Registra métricas de erro
            ERRORS.labels(
                method=method,
                endpoint=path,
                status=500
            ).inc()
            
            logger.error(f"Erro processando requisição: {e}")
            raise 