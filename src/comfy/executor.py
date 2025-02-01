"""
Executor para workflows do ComfyUI.
"""
from typing import Dict, Any, Optional, List
from fastapi import WebSocket
from datetime import datetime
import asyncio
import json
from uuid import UUID

from src.api.v2.schemas.comfy import (
    WorkflowExecutionStatus,
    ExecutionStatus,
    NodeExecutionStatus,
    WorkflowSettings
)
from src.comfy.client import ComfyClient
from src.core.gpu.manager import GPUManager
from src.monitoring.metrics import workflow_metrics

class ComfyExecutor:
    """
    Gerenciador de execução de workflows do ComfyUI.
    
    Responsabilidades:
    - Gerenciar fila de execução
    - Controlar status das execuções
    - Gerenciar conexões WebSocket
    - Integrar com métricas
    """
    
    def __init__(self):
        self.executions: Dict[str, WorkflowExecutionStatus] = {}
        self.clients: Dict[str, List[WebSocket]] = {}
        self.gpu_manager = GPUManager()
        self.comfy_client = ComfyClient()
        
        # Lock para sincronização
        self._lock = asyncio.Lock()
        
    async def execute_workflow(
        self,
        workflow: Dict[str, Any],
        settings: WorkflowSettings,
        execution_id: str,
        user_id: str
    ):
        """
        Executa um workflow do ComfyUI.
        """
        try:
            # Atualiza status para running
            async with self._lock:
                status = self.executions[execution_id]
                status.status = ExecutionStatus.RUNNING
                await self._notify_clients(execution_id, status)
            
            # Aloca GPU
            gpu_id = settings.gpu_id or await self.gpu_manager.allocate_gpu(
                vram_required=8,  # TODO: Estimar VRAM necessária
                priority=settings.priority
            )
            
            start_time = datetime.utcnow()
            
            try:
                # Executa workflow
                with workflow_metrics.execution_time.time():
                    result = await self.comfy_client.execute_workflow(
                        workflow=workflow,
                        gpu_id=gpu_id,
                        timeout=settings.timeout
                    )
                
                # Atualiza status para completed
                async with self._lock:
                    status = self.executions[execution_id]
                    status.status = ExecutionStatus.COMPLETED
                    status.finished_at = datetime.utcnow().isoformat()
                    
                    # Atualiza outputs dos nós
                    for node_id, node_result in result.items():
                        if node_id in status.nodes:
                            status.nodes[node_id].status = ExecutionStatus.COMPLETED
                            status.nodes[node_id].outputs = node_result
                            
                    await self._notify_clients(execution_id, status)
                    
            except Exception as e:
                # Atualiza status para failed
                async with self._lock:
                    status = self.executions[execution_id]
                    status.status = ExecutionStatus.FAILED
                    status.error = str(e)
                    status.finished_at = datetime.utcnow().isoformat()
                    await self._notify_clients(execution_id, status)
                    
            finally:
                # Libera GPU
                await self.gpu_manager.release_gpu(gpu_id)
                
        except Exception as e:
            print(f"Error executing workflow {execution_id}: {e}")
            
    async def get_execution_status(
        self,
        execution_id: str
    ) -> Optional[WorkflowExecutionStatus]:
        """
        Obtém status de uma execução.
        """
        async with self._lock:
            return self.executions.get(execution_id)
            
    async def cancel_execution(
        self,
        execution_id: str
    ):
        """
        Cancela uma execução em andamento.
        """
        async with self._lock:
            if execution_id not in self.executions:
                return
                
            status = self.executions[execution_id]
            if status.status == ExecutionStatus.RUNNING:
                # Cancela no ComfyUI
                await self.comfy_client.cancel_workflow(execution_id)
                
                # Atualiza status
                status.status = ExecutionStatus.CANCELLED
                status.finished_at = datetime.utcnow().isoformat()
                await self._notify_clients(execution_id, status)
                
    async def register_client(
        self,
        execution_id: str,
        websocket: WebSocket
    ):
        """
        Registra um cliente WebSocket para receber updates.
        """
        async with self._lock:
            if execution_id not in self.clients:
                self.clients[execution_id] = []
            self.clients[execution_id].append(websocket)
            
    async def unregister_client(
        self,
        execution_id: str,
        websocket: WebSocket
    ):
        """
        Remove um cliente WebSocket.
        """
        async with self._lock:
            if execution_id in self.clients:
                self.clients[execution_id].remove(websocket)
                
    async def _notify_clients(
        self,
        execution_id: str,
        status: WorkflowExecutionStatus
    ):
        """
        Notifica clientes WebSocket sobre mudanças de status.
        """
        if execution_id not in self.clients:
            return
            
        # Converte status para dict
        status_dict = status.model_dump()
        
        # Envia para todos os clientes
        for websocket in self.clients[execution_id]:
            try:
                await websocket.send_text(json.dumps(status_dict))
            except Exception as e:
                print(f"Error notifying client: {e}")
                # Remove cliente com erro
                await self.unregister_client(execution_id, websocket)