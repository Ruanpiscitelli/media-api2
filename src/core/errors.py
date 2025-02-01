"""
Exceções e handlers de erro unificados.
"""

from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from prometheus_client import Counter
import logging
import traceback

# Métricas
ERROR_COUNTS = Counter('error_count_total', 'Total de erros por tipo', ['type'])

logger = logging.getLogger(__name__)

class BaseError(Exception):
    """Classe base para exceções personalizadas"""
    def __init__(self, message: str = None):
        self.message = message
        super().__init__(self.message)

class APIError(HTTPException):
    """Erro base para exceções da API"""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "internal_error",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=message)
        self.error_code = error_code
        self.details = details or {}
        ERROR_COUNTS.labels(error_code).inc()

class ResourceError(APIError):
    pass

class ProcessingError(APIError):
    pass

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
class GPUError(BaseError):
    """Classe base para erros relacionados a GPU"""
    pass

class InsufficientVRAMError(GPUError):
    """
    Erro lançado quando não há VRAM suficiente para executar uma tarefa
    """
    def __init__(self, required_vram: int, available_vram: int, gpu_id: int = None):
        self.required_vram = required_vram
        self.available_vram = available_vram
        self.gpu_id = gpu_id
        message = f"VRAM insuficiente: necessário {required_vram/1e9:.1f}GB, disponível {available_vram/1e9:.1f}GB"
        if gpu_id is not None:
            message += f" na GPU {gpu_id}"
        super().__init__(message)

class PreemptionError(GPUError):
    """
    Erro lançado quando uma tarefa é interrompida por preempção
    """
    def __init__(self, task_id: str, gpu_id: int = None):
        self.task_id = task_id
        self.gpu_id = gpu_id
        message = f"Tarefa {task_id} foi interrompida por preempção"
        if gpu_id is not None:
            message += f" na GPU {gpu_id}"
        super().__init__(message)

class NoAvailableGPUError(GPUError):
    """
    Erro lançado quando não há GPUs disponíveis
    """
    def __init__(self):
        super().__init__("Não há GPUs disponíveis no momento")

class GPUNotFoundError(GPUError):
    """
    Erro lançado quando uma GPU específica não é encontrada
    """
    def __init__(self, gpu_id: int):
        super().__init__(f"GPU {gpu_id} não encontrada")

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

# Erros de API
class DiskSpaceError(ResourceError):
    """
    Erro lançado quando não há espaço em disco suficiente
    """
    def __init__(self, required_space: int, available_space: int):
        self.required_space = required_space
        self.available_space = available_space
        super().__init__(
            f"Espaço insuficiente em disco: necessário {required_space/1e9:.1f}GB, "
            f"disponível {available_space/1e9:.1f}GB"
        )

class MemoryError(ResourceError):
    """
    Erro lançado quando não há memória RAM suficiente
    """
    def __init__(self, required_memory: int, available_memory: int):
        self.required_memory = required_memory
        self.available_memory = available_memory
        super().__init__(
            f"Memória RAM insuficiente: necessário {required_memory/1e9:.1f}GB, "
            f"disponível {available_memory/1e9:.1f}GB"
        )

# Erros de Processamento
class GenerationError(ProcessingError):
    """
    Erro lançado quando há falha na geração de conteúdo
    """
    def __init__(self, content_type: str, reason: str = None):
        message = f"Falha na geração de {content_type}"
        if reason:
            message += f": {reason}"
        super().__init__(message)

# Handlers de Erro
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handler para erros da API"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": getattr(exc, "error_code", "internal_error"),
                "message": exc.detail,
                "details": getattr(exc, "details", {})
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

async def error_handler(
    request: Request,
    exc: Union[Exception, HTTPException]
) -> JSONResponse:
    """Handler global de erros"""
    
    # Log do erro
    error_details = {
        "path": str(request.url),
        "method": request.method,
        "error": str(exc),
        "traceback": traceback.format_exc()
    }
    logger.error(f"Error handling request: {error_details}")
    
    # Resposta para o cliente
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
        
    # Erro interno
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_id": str(request.state.request_id)
        }
    ) 