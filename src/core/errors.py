"""
Exceções e handlers de erro unificados.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from prometheus_client import Counter

# Métricas
ERROR_COUNTS = Counter('error_count_total', 'Total de erros por tipo', ['type'])

class APIError(Exception):
    """Erro base para todas as exceções da API"""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "internal_error",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        ERROR_COUNTS.labels(error_code).inc()
        super().__init__(message)

# Erros de Autenticação
class AuthenticationError(APIError):
    """Erro de autenticação"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="authentication_error"
        )

class AuthorizationError(APIError):
    """Erro de autorização"""
    def __init__(self, message: str = "Not authorized"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="authorization_error"
        )

# Erros de Validação
class ValidationError(APIError):
    """Erro de validação"""
    def __init__(self, message: str, details: Dict[str, Any]):
        super().__init__(
            message=message,
            status_code=422,
            error_code="validation_error",
            details=details
        )

class RateLimitError(APIError):
    """Erro de limite de requisições"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            status_code=429,
            error_code="rate_limit_error"
        )

# Erros de Recursos
class ResourceNotFoundError(APIError):
    """Erro de recurso não encontrado"""
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} with id {resource_id} not found",
            status_code=404,
            error_code="resource_not_found",
            details={"resource": resource, "id": resource_id}
        )

class ResourceConflictError(APIError):
    """Erro de conflito de recursos"""
    def __init__(self, message: str, details: Dict[str, Any]):
        super().__init__(
            message=message,
            status_code=409,
            error_code="resource_conflict",
            details=details
        )

# Erros de GPU
class GPUError(APIError):
    """Erro base para problemas com GPU"""
    def __init__(self, message: str, details: Dict[str, Any]):
        super().__init__(
            message=message,
            status_code=503,
            error_code="gpu_error",
            details=details
        )

class NoGPUAvailableError(GPUError):
    """Erro quando não há GPU disponível"""
    def __init__(self, required_vram: int):
        super().__init__(
            message="No GPU available with sufficient VRAM",
            details={"required_vram": required_vram}
        )

class GPUOutOfMemoryError(GPUError):
    """Erro de falta de memória na GPU"""
    def __init__(self, gpu_id: int, available_vram: int, required_vram: int):
        super().__init__(
            message=f"GPU {gpu_id} out of memory",
            details={
                "gpu_id": gpu_id,
                "available_vram": available_vram,
                "required_vram": required_vram
            }
        )

# Erros de Fila
class QueueError(APIError):
    """Erro base para problemas com fila"""
    def __init__(self, message: str, details: Dict[str, Any]):
        super().__init__(
            message=message,
            status_code=503,
            error_code="queue_error",
            details=details
        )

class QueueFullError(QueueError):
    """Erro quando a fila está cheia"""
    def __init__(self, queue_size: int):
        super().__init__(
            message="Task queue is full",
            details={"queue_size": queue_size}
        )

class TaskTimeoutError(QueueError):
    """Erro quando uma tarefa excede o tempo limite"""
    def __init__(self, task_id: str, timeout: int):
        super().__init__(
            message=f"Task {task_id} timed out after {timeout} seconds",
            details={"task_id": task_id, "timeout": timeout}
        )

# Erros de Modelo
class ModelError(APIError):
    """Erro base para problemas com modelos"""
    def __init__(self, message: str, details: Dict[str, Any]):
        super().__init__(
            message=message,
            status_code=500,
            error_code="model_error",
            details=details
        )

class ModelNotFoundError(ModelError):
    """Erro quando um modelo não é encontrado"""
    def __init__(self, model_id: str):
        super().__init__(
            message=f"Model {model_id} not found",
            details={"model_id": model_id}
        )

class ModelLoadError(ModelError):
    """Erro ao carregar um modelo"""
    def __init__(self, model_id: str, error: str):
        super().__init__(
            message=f"Failed to load model {model_id}",
            details={"model_id": model_id, "error": str(error)}
        )

# Handlers de Erro
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handler para erros da API"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )

async def validation_error_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handler para erros de validação do FastAPI"""
    ERROR_COUNTS.labels("validation_error").inc()
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "Validation error",
                "details": {
                    "errors": exc.errors(),
                    "body": exc.body
                }
            }
        }
    )

async def http_exception_handler(
    request: Request,
    exc: HTTPException
) -> JSONResponse:
    """Handler para exceções HTTP do FastAPI"""
    ERROR_COUNTS.labels("http_error").inc()
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "http_error",
                "message": exc.detail
            }
        }
    )

async def python_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handler para exceções Python não tratadas"""
    ERROR_COUNTS.labels("internal_error").inc()
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_error",
                "message": "Internal server error",
                "details": {
                    "type": type(exc).__name__,
                    "message": str(exc)
                }
            }
        }
    ) 