"""
Exceções customizadas e handlers
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from redis.exceptions import RedisError
import structlog

logger = structlog.get_logger()

class APIError(Exception):
    """Base para erros da API"""
    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code = code

async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
):
    """Handler para erros de validação"""
    logger.error(
        "validation_error",
        path=request.url.path,
        errors=exc.errors()
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body
        }
    )

async def sqlalchemy_exception_handler(
    request: Request, 
    exc: SQLAlchemyError
):
    """Handler para erros de banco de dados"""
    logger.error(
        "database_error",
        path=request.url.path,
        error=str(exc)
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database error occurred"}
    )

# Registrar handlers
app.add_exception_handler(
    RequestValidationError, 
    validation_exception_handler
)
app.add_exception_handler(
    SQLAlchemyError,
    sqlalchemy_exception_handler
) 