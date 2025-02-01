"""
Handlers de erro e exceções customizadas
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from typing import Union, Dict, Any

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Erro base da API"""
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

async def api_error_handler(
    request: Request,
    exc: APIError
) -> JSONResponse:
    """Handler para APIError"""
    logger.error(
        f"API Error: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details
        }
    )

async def validation_error_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handler para erros de validação"""
    logger.error(
        "Validation Error",
        extra={
            "errors": exc.errors(),
            "body": exc.body,
            "path": request.url.path
        }
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "details": exc.errors()
        }
    ) 