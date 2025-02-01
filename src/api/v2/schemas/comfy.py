"""
Schemas para integração com ComfyUI.
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum

class CachePolicy(str, Enum):
    """Política de cache para execução de workflows"""
    NO_CACHE = "no_cache"  # Não usa cache
    READ_ONLY = "read_only"  # Apenas lê do cache
    WRITE_ONLY = "write_only"  # Apenas escreve no cache
    READ_WRITE = "read_write"  # Lê e escreve no cache

class NodeInput(BaseModel):
    """Input de um nó do workflow"""
    type: str = Field(..., description="Tipo do input (int, float, string, etc)")
    value: Any = Field(..., description="Valor do input")
    is_required: bool = Field(default=True, description="Se o input é obrigatório")

class NodeOutput(BaseModel):
    """Output de um nó do workflow"""
    type: str = Field(..., description="Tipo do output (image, audio, etc)")
    name: str = Field(..., description="Nome do output")

class WorkflowNode(BaseModel):
    """Nó de um workflow do ComfyUI"""
    id: int = Field(..., description="ID único do nó")
    class_type: str = Field(..., description="Tipo/classe do nó")
    inputs: Dict[str, NodeInput] = Field(default_factory=dict, description="Inputs do nó")
    outputs: Dict[str, NodeOutput] = Field(default_factory=dict, description="Outputs do nó")

class WorkflowSettings(BaseModel):
    """Configurações para execução de workflow"""
    gpu_id: Optional[int] = Field(default=None, description="ID da GPU específica para usar")
    priority: int = Field(default=0, description="Prioridade do workflow (maior = mais prioritário)")
    cache_policy: CachePolicy = Field(default=CachePolicy.READ_WRITE, description="Política de cache")
    timeout: int = Field(default=300, description="Timeout em segundos")
    max_retries: int = Field(default=3, description="Número máximo de tentativas em caso de falha")

class WorkflowExecutionRequest(BaseModel):
    """Request para execução de workflow"""
    workflow: Dict[str, WorkflowNode] = Field(..., description="Workflow do ComfyUI em formato JSON")
    settings: WorkflowSettings = Field(default_factory=WorkflowSettings, description="Configurações de execução")
    webhook_url: Optional[str] = Field(default=None, description="URL para webhook de notificação")

class ExecutionStatus(str, Enum):
    """Status possíveis de uma execução"""
    QUEUED = "queued"  # Na fila
    RUNNING = "running"  # Em execução
    COMPLETED = "completed"  # Concluído com sucesso
    FAILED = "failed"  # Falhou
    CANCELLED = "cancelled"  # Cancelado

class NodeExecutionStatus(BaseModel):
    """Status de execução de um nó"""
    node_id: int = Field(..., description="ID do nó")
    status: ExecutionStatus = Field(..., description="Status atual")
    progress: float = Field(default=0, description="Progresso (0-100)")
    error: Optional[str] = Field(default=None, description="Mensagem de erro se houver")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Outputs gerados")

class WorkflowExecutionStatus(BaseModel):
    """Status completo de execução do workflow"""
    execution_id: str = Field(..., description="ID único da execução")
    status: ExecutionStatus = Field(..., description="Status geral")
    nodes: Dict[int, NodeExecutionStatus] = Field(..., description="Status por nó")
    started_at: str = Field(..., description="Timestamp de início")
    finished_at: Optional[str] = Field(default=None, description="Timestamp de conclusão")
    error: Optional[str] = Field(default=None, description="Erro geral se houver") 