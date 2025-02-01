"""
Cliente para comunicação com o ComfyUI.
"""
from typing import Dict, Any, Optional
import aiohttp
import json
import asyncio
from datetime import datetime

from src.comfy.config import ComfyConfig

class ComfyClient:
    """
    Cliente para comunicação com o ComfyUI via HTTP e WebSocket.
    
    Responsabilidades:
    - Comunicação HTTP com API do ComfyUI
    - Comunicação WebSocket para status em tempo real
    - Gerenciamento de conexões
    """
    
    def __init__(self):
        self.config = ComfyConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
        
    async def __aenter__(self):
        """Context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.disconnect()
        
    async def connect(self):
        """
        Estabelece conexão com o ComfyUI.
        """
        if not self.session:
            self.session = aiohttp.ClientSession(
                base_url=self.config.api_url,
                headers={"Content-Type": "application/json"}
            )
            
    async def disconnect(self):
        """
        Fecha conexão com o ComfyUI.
        """
        if self.session:
            await self.session.close()
            self.session = None
            
    async def execute_workflow(
        self,
        workflow: Dict[str, Any],
        gpu_id: int,
        timeout: float = 300
    ) -> Dict[str, Any]:
        """
        Executa um workflow no ComfyUI.
        
        Args:
            workflow: Workflow em formato JSON
            gpu_id: ID da GPU para execução
            timeout: Timeout em segundos
            
        Returns:
            Dict com resultados da execução
        """
        await self.connect()
        
        async with self._lock:
            try:
                # Prepara request
                data = {
                    "workflow": workflow,
                    "gpu_id": gpu_id
                }
                
                # Envia workflow
                async with self.session.post(
                    "/api/queue",
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    response.raise_for_status()
                    prompt_id = (await response.json())["prompt_id"]
                    
                # Aguarda conclusão via WebSocket
                result = await self._wait_for_completion(prompt_id, timeout)
                return result
                
            except aiohttp.ClientError as e:
                raise Exception(f"ComfyUI API error: {str(e)}")
                
    async def cancel_workflow(
        self,
        prompt_id: str
    ):
        """
        Cancela execução de um workflow.
        """
        await self.connect()
        
        async with self._lock:
            try:
                async with self.session.post(
                    f"/api/queue/{prompt_id}/cancel"
                ) as response:
                    response.raise_for_status()
                    
            except aiohttp.ClientError as e:
                raise Exception(f"ComfyUI API error: {str(e)}")
                
    async def get_workflow_status(
        self,
        prompt_id: str
    ) -> Dict[str, Any]:
        """
        Obtém status de um workflow.
        """
        await self.connect()
        
        async with self._lock:
            try:
                async with self.session.get(
                    f"/api/queue/{prompt_id}/status"
                ) as response:
                    response.raise_for_status()
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                raise Exception(f"ComfyUI API error: {str(e)}")
                
    async def _wait_for_completion(
        self,
        prompt_id: str,
        timeout: float
    ) -> Dict[str, Any]:
        """
        Aguarda conclusão de um workflow via WebSocket.
        """
        start_time = datetime.utcnow()
        
        try:
            # Conecta ao WebSocket
            async with self.session.ws_connect(
                f"{self.config.ws_url}/ws?clientId={prompt_id}"
            ) as ws:
                while True:
                    # Verifica timeout
                    if (datetime.utcnow() - start_time).total_seconds() > timeout:
                        raise TimeoutError("Workflow execution timeout")
                        
                    # Recebe mensagem
                    msg = await ws.receive_json()
                    
                    # Processa mensagem
                    if msg["type"] == "execution_start":
                        continue
                    elif msg["type"] == "execution_cached":
                        return msg["data"]
                    elif msg["type"] == "executing":
                        continue
                    elif msg["type"] == "progress":
                        continue
                    elif msg["type"] == "executed":
                        return msg["data"]
                    elif msg["type"] == "execution_error":
                        raise Exception(f"Workflow execution error: {msg['data']}")
                        
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise Exception(f"WebSocket error: {str(e)}")
            
    async def get_object_info(self) -> Dict[str, Any]:
        """
        Obtém informações sobre objetos disponíveis no ComfyUI.
        """
        await self.connect()
        
        async with self._lock:
            try:
                async with self.session.get("/object_info") as response:
                    response.raise_for_status()
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                raise Exception(f"ComfyUI API error: {str(e)}")
                
    async def get_history(self) -> Dict[str, Any]:
        """
        Obtém histórico de execuções.
        """
        await self.connect()
        
        async with self._lock:
            try:
                async with self.session.get("/history") as response:
                    response.raise_for_status()
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                raise Exception(f"ComfyUI API error: {str(e)}")
                
    async def get_system_stats(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do sistema.
        """
        await self.connect()
        
        async with self._lock:
            try:
                async with self.session.get("/system/stats") as response:
                    response.raise_for_status()
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                raise Exception(f"ComfyUI API error: {str(e)}")

# Instância global do cliente
comfy_client = ComfyClient() 