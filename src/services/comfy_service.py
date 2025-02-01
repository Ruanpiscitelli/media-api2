"""
Serviço para gerenciar a comunicação com o ComfyUI.
"""

import aiohttp
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import websockets
from core.config import settings

logger = logging.getLogger(__name__)

class ComfyUIError(Exception):
    """Exceção customizada para erros do ComfyUI"""
    pass

class ComfyUIService:
    def __init__(self):
        """
        Inicializa o serviço ComfyUI.
        """
        self.host = settings.COMFY_HOST
        self.port = settings.COMFY_PORT
        self.api_url = settings.COMFY_API_URL
        self.ws_url = settings.COMFY_WS_URL
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Diretório base do projeto
        self.base_path = Path(__file__).parent.parent.parent
        self.workflows_path = self.base_path / "workflows"
    
    async def __aenter__(self):
        """Cria a sessão HTTP quando usado como context manager"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Fecha a sessão HTTP quando usado como context manager"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def ensure_session(self):
        """Garante que existe uma sessão HTTP ativa"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def load_workflow(self, workflow_name: str) -> Dict[str, Any]:
        """
        Carrega um workflow do disco.
        
        Args:
            workflow_name: Nome do arquivo do workflow (sem extensão)
            
        Returns:
            Dict contendo o workflow
        """
        workflow_path = self.workflows_path / f"{workflow_name}.json"
        
        if not workflow_path.exists():
            raise ComfyUIError(f"Workflow não encontrado: {workflow_name}")
        
        try:
            return json.loads(workflow_path.read_text())
        except json.JSONDecodeError:
            raise ComfyUIError(f"Erro ao decodificar workflow: {workflow_name}")
    
    async def execute_workflow(
        self,
        workflow: Dict[str, Any],
        prompt_inputs: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Executa um workflow no ComfyUI.
        
        Args:
            workflow: Workflow a ser executado
            prompt_inputs: Inputs para substituir no workflow
            
        Returns:
            ID do prompt executado
        """
        await self.ensure_session()
        
        # Substituir inputs se fornecidos
        if prompt_inputs:
            workflow = self._replace_workflow_inputs(workflow, prompt_inputs)
        
        try:
            async with self.session.post(
                f"{self.api_url}/prompt",
                json={"prompt": workflow}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ComfyUIError(f"Erro ao executar workflow: {error_text}")
                
                data = await response.json()
                return data["prompt_id"]
        except aiohttp.ClientError as e:
            raise ComfyUIError(f"Erro de conexão com ComfyUI: {str(e)}")
    
    async def wait_for_execution(self, prompt_id: str) -> Dict[str, Any]:
        """
        Aguarda a execução de um prompt ser concluída.
        
        Args:
            prompt_id: ID do prompt a aguardar
            
        Returns:
            Dict contendo o resultado da execução
        """
        try:
            async with websockets.connect(self.ws_url) as websocket:
                while True:
                    msg = await websocket.recv()
                    data = json.loads(msg)
                    
                    if data["type"] == "executing":
                        if data["data"]["prompt_id"] == prompt_id:
                            logger.info(f"Executando nó: {data['data']['node']}")
                    
                    elif data["type"] == "executed":
                        if data["data"]["prompt_id"] == prompt_id:
                            return data["data"]["output"]
                    
                    elif data["type"] == "execution_error":
                        if data["data"]["prompt_id"] == prompt_id:
                            raise ComfyUIError(f"Erro na execução: {data['data']['error']}")
        except websockets.WebSocketException as e:
            raise ComfyUIError(f"Erro na conexão WebSocket: {str(e)}")
    
    def _replace_workflow_inputs(
        self,
        workflow: Dict[str, Any],
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Substitui inputs em um workflow.
        
        Args:
            workflow: Workflow original
            inputs: Novos inputs
            
        Returns:
            Workflow com inputs substituídos
        """
        workflow = workflow.copy()
        
        for node_id, node in workflow.items():
            if "inputs" in node and isinstance(node["inputs"], dict):
                for input_name, input_value in node["inputs"].items():
                    if input_name in inputs:
                        node["inputs"][input_name] = inputs[input_name]
        
        return workflow
    
    async def get_history(self) -> List[Dict[str, Any]]:
        """
        Obtém o histórico de execuções.
        
        Returns:
            Lista de execuções
        """
        await self.ensure_session()
        
        try:
            async with self.session.get(f"{self.api_url}/history") as response:
                if response.status != 200:
                    raise ComfyUIError("Erro ao obter histórico")
                return await response.json()
        except aiohttp.ClientError as e:
            raise ComfyUIError(f"Erro de conexão: {str(e)}")
    
    async def interrupt_execution(self) -> None:
        """Interrompe a execução atual"""
        await self.ensure_session()
        
        try:
            async with self.session.post(f"{self.api_url}/interrupt") as response:
                if response.status != 200:
                    raise ComfyUIError("Erro ao interromper execução")
        except aiohttp.ClientError as e:
            raise ComfyUIError(f"Erro de conexão: {str(e)}") 