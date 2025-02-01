"""
Endpoints para gerenciamento de workflows do ComfyUI.
Permite criar, executar e gerenciar workflows personalizados.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import json

from src.services.auth import get_current_user
from src.core.rate_limit import rate_limiter
from src.comfy.workflow_manager import WorkflowManager
from src.comfy.executor import ComfyExecutor
from src.core.gpu.manager import GPUManager
from src.monitoring.metrics import workflow_metrics

router = APIRouter(prefix="/workflows", tags=["Workflows"])
logger = logging.getLogger(__name__)

# Instâncias dos managers
workflow_manager = WorkflowManager()
executor = ComfyExecutor()
gpu_manager = GPUManager()

# Schemas
class WorkflowMetadata(BaseModel):
    """Metadados de um workflow"""
    name: str = Field(..., description="Nome do workflow")
    description: Optional[str] = Field(None, description="Descrição do workflow")
    version: str = Field(..., description="Versão do workflow")
    author: str = Field(..., description="Autor do workflow")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None

class WorkflowCreateRequest(BaseModel):
    """Request para criar workflow"""
    metadata: WorkflowMetadata
    workflow: Dict[str, Any] = Field(..., description="Workflow do ComfyUI")
    is_public: bool = Field(default=False, description="Se o workflow é público")

class WorkflowExecuteRequest(BaseModel):
    """Request para executar workflow"""
    workflow_id: str = Field(..., description="ID do workflow")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    gpu_id: Optional[int] = Field(None, description="ID da GPU específica")
    priority: int = Field(default=0, description="Prioridade (maior = mais prioritário)")
    webhook_url: Optional[str] = None

class WorkflowUpdateRequest(BaseModel):
    """Request para atualizar workflow"""
    description: Optional[str] = None
    workflow: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    version: Optional[str] = None

# Endpoints
@router.post("/create", response_model=Dict[str, Any])
async def create_workflow(
    request: WorkflowCreateRequest,
    current_user = Depends(get_current_user)
):
    """
    Cria um novo workflow personalizado.
    """
    try:
        # Validar workflow
        workflow_manager.validate_workflow(request.workflow)
        
        # Criar workflow
        workflow = {
            "metadata": {
                **request.metadata.model_dump(),
                "author": current_user.username,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            "workflow": request.workflow,
            "is_public": request.is_public
        }
        
        # Salvar
        workflow_id = await workflow_manager.save_workflow(workflow)
        
        return {
            "status": "success",
            "workflow_id": workflow_id,
            "message": "Workflow criado com sucesso"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro criando workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute", response_model=Dict[str, Any])
async def execute_workflow(
    request: WorkflowExecuteRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    rate_limit = Depends(rate_limiter)
):
    """
    Executa um workflow.
    """
    try:
        # Carregar workflow
        workflow = await workflow_manager.get_workflow(request.workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow não encontrado")
            
        # Verificar permissão
        if not workflow["is_public"] and workflow["metadata"]["author"] != current_user.username:
            raise HTTPException(status_code=403, detail="Sem permissão para executar este workflow")
            
        # Alocar GPU
        gpu_id = request.gpu_id or await gpu_manager.allocate_gpu(
            vram_required=8,  # TODO: Estimar VRAM necessária
            priority=request.priority
        )
        
        # Iniciar execução em background
        execution_id = await executor.execute_workflow(
            workflow=workflow["workflow"],
            parameters=request.parameters,
            gpu_id=gpu_id,
            user_id=current_user.id,
            webhook_url=request.webhook_url
        )
        
        return {
            "status": "success",
            "execution_id": execution_id,
            "message": "Execução iniciada com sucesso"
        }
        
    except Exception as e:
        logger.error(f"Erro executando workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list", response_model=Dict[str, Any])
async def list_workflows(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    author: Optional[str] = None,
    is_public: Optional[bool] = None,
    current_user = Depends(get_current_user)
):
    """
    Lista workflows disponíveis.
    """
    try:
        workflows = await workflow_manager.list_workflows(
            page=page,
            page_size=page_size,
            category=category,
            tags=tags,
            author=author,
            is_public=is_public
        )
        
        return {
            "status": "success",
            "workflows": workflows["items"],
            "total": workflows["total"],
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"Erro listando workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}", response_model=Dict[str, Any])
async def get_workflow(
    workflow_id: str,
    current_user = Depends(get_current_user)
):
    """
    Obtém detalhes de um workflow.
    """
    try:
        workflow = await workflow_manager.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow não encontrado")
            
        # Verificar permissão
        if not workflow["is_public"] and workflow["metadata"]["author"] != current_user.username:
            raise HTTPException(status_code=403, detail="Sem permissão para ver este workflow")
            
        return {
            "status": "success",
            "workflow": workflow
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro obtendo workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{workflow_id}", response_model=Dict[str, Any])
async def update_workflow(
    workflow_id: str,
    request: WorkflowUpdateRequest,
    current_user = Depends(get_current_user)
):
    """
    Atualiza um workflow existente.
    """
    try:
        # Verificar existência
        workflow = await workflow_manager.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow não encontrado")
            
        # Verificar permissão
        if workflow["metadata"]["author"] != current_user.username:
            raise HTTPException(status_code=403, detail="Sem permissão para editar este workflow")
            
        # Atualizar
        updated = await workflow_manager.update_workflow(
            workflow_id=workflow_id,
            description=request.description,
            workflow=request.workflow,
            is_public=request.is_public,
            version=request.version
        )
        
        return {
            "status": "success",
            "workflow": updated,
            "message": "Workflow atualizado com sucesso"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro atualizando workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_user = Depends(get_current_user)
):
    """
    Remove um workflow.
    """
    try:
        # Verificar existência
        workflow = await workflow_manager.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow não encontrado")
            
        # Verificar permissão
        if workflow["metadata"]["author"] != current_user.username:
            raise HTTPException(status_code=403, detail="Sem permissão para remover este workflow")
            
        # Remover
        await workflow_manager.delete_workflow(workflow_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Workflow removido com sucesso"
            }
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro removendo workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/executions/{execution_id}", response_model=Dict[str, Any])
async def get_execution_status(
    execution_id: str,
    current_user = Depends(get_current_user)
):
    """
    Obtém status de uma execução.
    """
    try:
        status = await executor.get_execution_status(execution_id)
        if not status:
            raise HTTPException(status_code=404, detail="Execução não encontrada")
            
        # Verificar permissão
        if status.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Sem permissão para ver esta execução")
            
        return {
            "status": "success",
            "execution": status.model_dump()
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro obtendo status da execução: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate", response_model=Dict[str, Any])
async def validate_workflow(
    workflow: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """
    Valida um workflow sem executá-lo.
    """
    try:
        # Validar workflow
        is_valid = workflow_manager.validate_workflow(workflow)
        
        return {
            "status": "success",
            "is_valid": is_valid
        }
        
    except ValueError as e:
        return {
            "status": "error",
            "is_valid": False,
            "errors": [str(e)]
        }
    except Exception as e:
        logger.error(f"Erro validando workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/fork", response_model=Dict[str, Any])
async def fork_workflow(
    workflow_id: str,
    current_user = Depends(get_current_user)
):
    """
    Cria uma cópia de um workflow existente.
    """
    try:
        # Carregar workflow original
        original = await workflow_manager.get_workflow(workflow_id)
        if not original:
            raise HTTPException(status_code=404, detail="Workflow não encontrado")
            
        # Verificar permissão
        if not original["is_public"] and original["metadata"]["author"] != current_user.username:
            raise HTTPException(status_code=403, detail="Sem permissão para fork deste workflow")
            
        # Criar cópia
        metadata = original["metadata"].copy()
        metadata["name"] = f"{metadata['name']}_fork"
        metadata["author"] = current_user.username
        metadata["created_at"] = datetime.utcnow()
        metadata["updated_at"] = datetime.utcnow()
        
        workflow = {
            "metadata": metadata,
            "workflow": original["workflow"],
            "is_public": False  # Fork sempre começa privado
        }
        
        # Salvar
        workflow_id = await workflow_manager.save_workflow(workflow)
        
        return {
            "status": "success",
            "workflow_id": workflow_id,
            "message": "Workflow fork criado com sucesso"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro criando fork do workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/executions", response_model=Dict[str, Any])
async def list_executions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Lista execuções de workflows do usuário.
    """
    try:
        executions = await executor.list_executions(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            status=status
        )
        
        return {
            "status": "success",
            "executions": executions["items"],
            "total": executions["total"],
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"Erro listando execuções: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    current_user = Depends(get_current_user)
):
    """
    Cancela uma execução em andamento.
    """
    try:
        status = await executor.get_execution_status(execution_id)
        if not status:
            raise HTTPException(status_code=404, detail="Execução não encontrada")
            
        # Verificar permissão
        if status.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Sem permissão para cancelar esta execução")
            
        await executor.cancel_execution(execution_id)
        
        return {
            "status": "success",
            "message": "Execução cancelada com sucesso"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro cancelando execução: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/executions/{execution_id}/logs", response_model=Dict[str, Any])
async def get_execution_logs(
    execution_id: str,
    current_user = Depends(get_current_user)
):
    """
    Obtém logs detalhados de uma execução.
    """
    try:
        status = await executor.get_execution_status(execution_id)
        if not status:
            raise HTTPException(status_code=404, detail="Execução não encontrada")
            
        # Verificar permissão
        if status.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Sem permissão para ver logs desta execução")
            
        logs = await executor.get_execution_logs(execution_id)
        
        return {
            "status": "success",
            "logs": logs
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro obtendo logs da execução: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", response_model=Dict[str, Any])
async def search_workflows(
    query: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user = Depends(get_current_user)
):
    """
    Pesquisa workflows por texto.
    """
    try:
        results = await workflow_manager.search_workflows(
            query=query,
            page=page,
            page_size=page_size,
            user_id=current_user.id
        )
        
        return {
            "status": "success",
            "workflows": results["items"],
            "total": results["total"],
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"Erro pesquisando workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/share")
async def share_workflow(
    workflow_id: str,
    users: List[str],
    current_user = Depends(get_current_user)
):
    """
    Compartilha um workflow com outros usuários.
    """
    try:
        # Verificar existência
        workflow = await workflow_manager.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow não encontrado")
            
        # Verificar permissão
        if workflow["metadata"]["author"] != current_user.username:
            raise HTTPException(status_code=403, detail="Sem permissão para compartilhar este workflow")
            
        # Compartilhar
        await workflow_manager.share_workflow(
            workflow_id=workflow_id,
            users=users
        )
        
        return {
            "status": "success",
            "message": "Workflow compartilhado com sucesso"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro compartilhando workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/export")
async def export_workflow(
    workflow_id: str,
    current_user = Depends(get_current_user)
):
    """
    Exporta um workflow para formato portável.
    """
    try:
        # Verificar existência
        workflow = await workflow_manager.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow não encontrado")
            
        # Verificar permissão
        if not workflow["is_public"] and workflow["metadata"]["author"] != current_user.username:
            raise HTTPException(status_code=403, detail="Sem permissão para exportar este workflow")
            
        # Exportar
        exported = await workflow_manager.export_workflow(workflow_id)
        
        return JSONResponse(
            content=exported,
            headers={
                "Content-Disposition": f"attachment; filename={workflow['metadata']['name']}.json"
            }
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro exportando workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import")
async def import_workflow(
    workflow_file: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """
    Importa um workflow de um arquivo.
    """
    try:
        # Validar arquivo
        if not workflow_manager.validate_workflow_file(workflow_file):
            raise HTTPException(status_code=400, detail="Arquivo de workflow inválido")
            
        # Importar
        workflow_id = await workflow_manager.import_workflow(
            workflow_file=workflow_file,
            user_id=current_user.id
        )
        
        return {
            "status": "success",
            "workflow_id": workflow_id,
            "message": "Workflow importado com sucesso"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro importando workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=Dict[str, Any])
async def get_workflow_stats(
    workflow_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Obtém estatísticas de uso de workflows.
    """
    try:
        stats = await workflow_manager.get_stats(
            workflow_id=workflow_id,
            user_id=current_user.id
        )
        
        return {
            "status": "success",
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Erro obtendo estatísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 