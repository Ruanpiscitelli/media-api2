"""
Schemas para sistema de templates do ComfyUI.
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class TemplateParameterType(str, Enum):
    """Tipos de parâmetros suportados em templates"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ENUM = "enum"
    IMAGE = "image"
    MODEL = "model"
    LORA = "lora"
    EMBEDDING = "embedding"
    
class TemplateParameter(BaseModel):
    """Definição de um parâmetro de template"""
    name: str = Field(..., description="Nome do parâmetro")
    type: TemplateParameterType = Field(..., description="Tipo do parâmetro")
    description: str = Field(..., description="Descrição do parâmetro")
    default: Optional[Any] = Field(default=None, description="Valor padrão")
    required: bool = Field(default=True, description="Se o parâmetro é obrigatório")
    min_value: Optional[float] = Field(default=None, description="Valor mínimo (para números)")
    max_value: Optional[float] = Field(default=None, description="Valor máximo (para números)")
    enum_values: Optional[List[str]] = Field(default=None, description="Valores possíveis para enums")
    
class TemplateMetadata(BaseModel):
    """Metadados de um template"""
    name: str = Field(..., description="Nome do template")
    version: str = Field(..., description="Versão do template (semver)")
    description: str = Field(..., description="Descrição do template")
    author: str = Field(..., description="Autor do template")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Data de criação")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Data da última atualização")
    tags: List[str] = Field(default_factory=list, description="Tags para categorização")
    category: Optional[str] = Field(default=None, description="Categoria do template")
    preview_image: Optional[str] = Field(default=None, description="URL da imagem de preview")
    
class TemplateDefinition(BaseModel):
    """Definição completa de um template"""
    metadata: TemplateMetadata = Field(..., description="Metadados do template")
    parameters: Dict[str, TemplateParameter] = Field(
        default_factory=dict,
        description="Parâmetros configuráveis"
    )
    workflow: Dict[str, Any] = Field(..., description="Workflow base do ComfyUI")
    parameter_mappings: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Mapeamento de parâmetros para nós do workflow (param -> [node_id.input_name, ...])"
    )
    required_models: Dict[str, str] = Field(
        default_factory=dict,
        description="Modelos necessários (nome -> hash)"
    )
    example_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Exemplos de parâmetros"
    )
    
class TemplateCreateRequest(BaseModel):
    """Request para criar um novo template"""
    name: str = Field(..., description="Nome do template")
    description: str = Field(..., description="Descrição do template")
    workflow: Dict[str, Any] = Field(..., description="Workflow base")
    parameters: Dict[str, TemplateParameter] = Field(
        default_factory=dict,
        description="Parâmetros configuráveis"
    )
    parameter_mappings: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Mapeamento de parâmetros"
    )
    tags: List[str] = Field(default_factory=list, description="Tags")
    category: Optional[str] = Field(default=None, description="Categoria")
    
class TemplateUpdateRequest(BaseModel):
    """Request para atualizar um template existente"""
    description: Optional[str] = Field(default=None, description="Nova descrição")
    workflow: Optional[Dict[str, Any]] = Field(default=None, description="Novo workflow base")
    parameters: Optional[Dict[str, TemplateParameter]] = Field(
        default=None,
        description="Novos parâmetros"
    )
    parameter_mappings: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Novo mapeamento de parâmetros"
    )
    tags: Optional[List[str]] = Field(default=None, description="Novas tags")
    category: Optional[str] = Field(default=None, description="Nova categoria")
    
class TemplateListResponse(BaseModel):
    """Response para listagem de templates"""
    templates: List[TemplateMetadata] = Field(..., description="Lista de templates")
    total: int = Field(..., description="Total de templates")
    page: int = Field(..., description="Página atual")
    page_size: int = Field(..., description="Tamanho da página")
    
class TemplateVersionInfo(BaseModel):
    """Informações de uma versão específica de template"""
    version: str = Field(..., description="Número da versão")
    created_at: datetime = Field(..., description="Data de criação")
    author: str = Field(..., description="Autor da versão")
    changelog: str = Field(..., description="Descrição das mudanças")
    
class TemplateVersionsResponse(BaseModel):
    """Response para listagem de versões de um template"""
    template_name: str = Field(..., description="Nome do template")
    versions: List[TemplateVersionInfo] = Field(..., description="Lista de versões") 