"""
Gerenciador de workflows do ComfyUI.
"""
from typing import Dict, Any, List, Optional
import json
from pathlib import Path
import asyncio
import websockets
import logging
from src.core.config import settings

from src.comfy.config import ComfyConfig
from src.comfy.workflow_validator import WorkflowValidator

logger = logging.getLogger(__name__)

class ComfyWorkflowManager:
    """
    Gerenciador de workflows do ComfyUI.
    
    Responsabilidades:
    - Carregar/salvar workflows
    - Validar workflows
    - Gerenciar templates
    - Cache de workflows
    """
    
    def __init__(self):
        self.config = ComfyConfig()
        self.validator = WorkflowValidator()
        
        # Cache de workflows
        self._workflow_cache: Dict[str, Dict[str, Any]] = {}
        
        self.ws_url = f"ws://{settings.COMFY_HOST}:{settings.COMFY_PORT}/ws"
        self.api_url = f"http://{settings.COMFY_HOST}:{settings.COMFY_PORT}/api"
        self.workflows_dir = Path("workflows")
        self.workflows_dir.mkdir(exist_ok=True)
        
    def validate_workflow(self, workflow: Dict[str, Any]) -> bool:
        """
        Valida um workflow.
        
        Args:
            workflow: Workflow em formato JSON
            
        Returns:
            True se válido, False caso contrário
            
        Raises:
            ValueError: Se o workflow for inválido
        """
        return self.validator.validate(workflow)
        
    def load_workflow(self, workflow_name: str) -> Dict[str, Any]:
        """
        Carrega um workflow do disco.
        
        Args:
            workflow_name: Nome do workflow
            
        Returns:
            Workflow em formato JSON
            
        Raises:
            FileNotFoundError: Se o workflow não existir
        """
        # Verifica cache
        if workflow_name in self._workflow_cache:
            return self._workflow_cache[workflow_name]
            
        # Carrega do disco
        workflow_path = self.workflows_dir / f"{workflow_name}.json"
        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow não encontrado: {workflow_name}")
            
        with open(workflow_path, "r") as f:
            workflow = json.load(f)
            
        # Valida
        self.validate_workflow(workflow)
        
        # Adiciona ao cache
        self._workflow_cache[workflow_name] = workflow
        
        return workflow
        
    def save_workflow(
        self,
        workflow_name: str,
        workflow: Dict[str, Any]
    ):
        """
        Salva um workflow no disco.
        
        Args:
            workflow_name: Nome do workflow
            workflow: Workflow em formato JSON
        """
        # Valida
        self.validate_workflow(workflow)
        
        # Salva no disco
        workflow_path = self.workflows_dir / f"{workflow_name}.json"
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(workflow_path, "w") as f:
            json.dump(workflow, f, indent=2)
            
        # Atualiza cache
        self._workflow_cache[workflow_name] = workflow
        
    def list_workflows(self) -> List[str]:
        """
        Lista workflows disponíveis.
        
        Returns:
            Lista de nomes de workflows
        """
        workflows = []
        for path in self.workflows_dir.glob("*.json"):
            workflows.append(path.stem)
        return sorted(workflows)
        
    def delete_workflow(self, workflow_name: str):
        """
        Remove um workflow.
        
        Args:
            workflow_name: Nome do workflow
            
        Raises:
            FileNotFoundError: Se o workflow não existir
        """
        workflow_path = self.workflows_dir / f"{workflow_name}.json"
        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow não encontrado: {workflow_name}")
            
        # Remove do disco
        workflow_path.unlink()
        
        # Remove do cache
        self._workflow_cache.pop(workflow_name, None)
        
    def clear_cache(self):
        """Limpa cache de workflows."""
        self._workflow_cache.clear()
        
    def get_template(self, template_name: str) -> Dict[str, Any]:
        """
        Carrega um template de workflow.
        
        Args:
            template_name: Nome do template
            
        Returns:
            Template em formato JSON
            
        Raises:
            FileNotFoundError: Se o template não existir
        """
        template_path = self.config.base_dir / "templates" / f"{template_name}.json"
        if not template_path.exists():
            raise FileNotFoundError(f"Template não encontrado: {template_name}")
            
        with open(template_path, "r") as f:
            return json.load(f)
            
    def list_templates(self) -> List[str]:
        """
        Lista templates disponíveis.
        
        Returns:
            Lista de nomes de templates
        """
        templates = []
        templates_dir = self.config.base_dir / "templates"
        if templates_dir.exists():
            for path in templates_dir.glob("*.json"):
                templates.append(path.stem)
        return sorted(templates)
        
    def create_from_template(
        self,
        template_name: str,
        workflow_name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cria um workflow a partir de um template.
        
        Args:
            template_name: Nome do template
            workflow_name: Nome do novo workflow
            params: Parâmetros para customizar o template
            
        Returns:
            Workflow criado
        """
        # Carrega template
        template = self.get_template(template_name)
        
        # Aplica parâmetros
        if params:
            template = self._apply_template_params(template, params)
            
        # Salva novo workflow
        self.save_workflow(workflow_name, template)
        
        return template
        
    def _apply_template_params(
        self,
        template: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Aplica parâmetros em um template.
        
        Args:
            template: Template em formato JSON
            params: Parâmetros para aplicar
            
        Returns:
            Template com parâmetros aplicados
        """
        # TODO: Implementar lógica de substituição de parâmetros
        # Por enquanto apenas retorna o template original
        return template 

    async def execute_workflow(
        self, 
        workflow: Dict,
        prompt_inputs: Dict[str, Any],
        client_id: Optional[str] = None
    ) -> Dict:
        """
        Executa um workflow com os inputs fornecidos.
        
        Args:
            workflow: Workflow em formato API JSON
            prompt_inputs: Inputs para o workflow
            client_id: ID opcional do cliente
        """
        try:
            # Atualizar inputs no workflow
            workflow = self._update_workflow_inputs(workflow, prompt_inputs)
            
            # Conectar ao websocket
            async with websockets.connect(
                f"{self.ws_url}?clientId={client_id or 'api'}"
            ) as ws:
                # Enviar workflow
                await ws.send(json.dumps({
                    "type": "execute",
                    "data": workflow
                }))
                
                # Aguardar resposta
                while True:
                    msg = json.loads(await ws.recv())
                    
                    if msg["type"] == "executed":
                        return msg["data"]
                    elif msg["type"] == "error":
                        raise RuntimeError(f"Erro executando workflow: {msg['data']}")
                        
        except Exception as e:
            logger.error(f"Erro executando workflow: {e}")
            raise

    def _update_workflow_inputs(self, workflow: Dict, inputs: Dict) -> Dict:
        """Atualiza os inputs de um workflow"""
        updated = workflow.copy()
        
        for node_id, node in updated.items():
            if "inputs" in node:
                for input_name, input_value in node["inputs"].items():
                    if input_name in inputs:
                        node["inputs"][input_name] = inputs[input_name]
                        
        return updated

    async def get_node_info(self) -> Dict:
        """Obtém informações sobre os nós disponíveis"""
        # Fazer requisição HTTP para /object_info
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/object_info") as resp:
                return await resp.json() 