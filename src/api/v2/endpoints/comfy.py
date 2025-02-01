"""
Endpoints para integração com ComfyUI.
"""
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from uuid import uuid4
from datetime import datetime

from src.api.v2.schemas.comfy import (
    WorkflowExecutionRequest,
    WorkflowExecutionStatus,
    ExecutionStatus,
    NodeExecutionStatus
)
from src.comfy.executor import ComfyExecutor
from src.comfy.workflow_manager import WorkflowManager
from src.core.gpu.manager import GPUManager
from src.services.auth import get_current_user
from src.monitoring.metrics import workflow_metrics
from src.core.dependencies import get_comfy
from src.services.comfy_server import ComfyServer

router = APIRouter(prefix="/comfy", tags=["ComfyUI Integration"])

# Instâncias dos managers (devem ser inicializadas na startup da aplicação)
workflow_manager = WorkflowManager()
gpu_manager = GPUManager()
executor = ComfyExecutor()

@router.post("/workflow/execute", response_model=WorkflowExecutionStatus)
async def execute_workflow(
    request: WorkflowExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """
    Executa um workflow do ComfyUI.
    
    - Valida o workflow
    - Aloca recursos (GPU)
    - Inicia execução em background
    - Retorna ID para acompanhamento
    """
    try:
        # Valida o workflow
        workflow_manager.validate_workflow(request.workflow)
        
        # Gera ID único para a execução
        execution_id = str(uuid4())
        
        # Prepara status inicial
        status = WorkflowExecutionStatus(
            execution_id=execution_id,
            status=ExecutionStatus.QUEUED,
            nodes={},
            started_at=datetime.utcnow().isoformat()
        )
        
        # Inicializa status para cada nó
        for node_id in request.workflow:
            status.nodes[node_id] = NodeExecutionStatus(
                node_id=node_id,
                status=ExecutionStatus.QUEUED
            )
        
        # Adiciona à fila de execução
        background_tasks.add_task(
            executor.execute_workflow,
            workflow=request.workflow,
            settings=request.settings,
            execution_id=execution_id,
            user_id=current_user.id
        )
        
        return status
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/workflow/status/{execution_id}", response_model=WorkflowExecutionStatus)
async def get_workflow_status(
    execution_id: str,
    current_user = Depends(get_current_user)
):
    """
    Obtém o status atual de execução de um workflow.
    """
    try:
        status = await executor.get_execution_status(execution_id)
        if not status:
            raise HTTPException(status_code=404, detail="Execution not found")
            
        # Verifica permissão
        if status.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this execution")
            
        return status
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/workflow/cancel/{execution_id}")
async def cancel_workflow(
    execution_id: str,
    current_user = Depends(get_current_user)
):
    """
    Cancela a execução de um workflow.
    """
    try:
        status = await executor.get_execution_status(execution_id)
        if not status:
            raise HTTPException(status_code=404, detail="Execution not found")
            
        # Verifica permissão
        if status.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to cancel this execution")
            
        await executor.cancel_execution(execution_id)
        return JSONResponse(content={"message": "Execution cancelled successfully"})
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.websocket("/workflow/stream/{execution_id}")
async def stream_workflow(
    websocket: WebSocket,
    execution_id: str
):
    """
    Stream de status e previews via WebSocket.
    """
    try:
        await websocket.accept()
        
        # Registra cliente para receber updates
        await executor.register_client(execution_id, websocket)
        
        try:
            while True:
                # Mantém conexão aberta e processa mensagens do cliente
                data = await websocket.receive_text()
                
                # Processa comandos do cliente (ex: cancelar execução)
                if data == "cancel":
                    await executor.cancel_execution(execution_id)
                    
        except Exception as e:
            print(f"WebSocket error: {e}")
            
        finally:
            # Remove cliente ao fechar conexão
            await executor.unregister_client(execution_id, websocket)
            
    except Exception as e:
        print(f"WebSocket connection failed: {e}")

@router.get("/workflow/results/{execution_id}")
async def get_workflow_results(
    execution_id: str,
    current_user = Depends(get_current_user)
):
    """
    Obtém os resultados finais de um workflow executado.
    """
    try:
        results = await executor.get_execution_results(execution_id)
        if not results:
            raise HTTPException(status_code=404, detail="Results not found")
            
        # Verifica permissão
        if results.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view these results")
            
        return results
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status")
async def get_comfy_status(
    comfy: ComfyServer = Depends(get_comfy)
):
    """Retorna status do servidor ComfyUI."""
    return await comfy.get_status() 