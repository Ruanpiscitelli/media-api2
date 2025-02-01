"""
Gerenciador de workflows do ComfyUI.
Responsável por carregar, validar e executar workflows.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

import aiohttp
from pydantic import BaseModel

from src.core.config import settings

logger = logging.getLogger(__name__)

class WorkflowTemplate(BaseModel):
    """Modelo para template de workflow."""
    name: str
    description: str
    category: str
    file_path: Path
    metadata: Dict = {}
    node_map: Dict[str, str] = {}  # Mapa de nós para facilitar injeção
    default_inputs: Dict[str, Union[str, int, float]] = {}

class WorkflowManager:
    """Gerenciador de workflows do ComfyUI."""
    
    def __init__(self):
        """Inicializa o gerenciador de workflows."""
        self.workflow_dir = Path(settings.WORKFLOW_DIR)
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.comfy_api_url = f"http://{settings.COMFYUI_HOST}:{settings.COMFYUI_PORT}/api"
        self.cache: Dict[str, Dict] = {}
        
    async def load_templates(self) -> None:
        """Carrega todos os templates de workflow disponíveis."""
        for category in ["base", "custom"]:
            category_path = self.workflow_dir / category
            if not category_path.exists():
                logger.warning(f"Diretório de categoria {category} não encontrado")
                continue
                
            for workflow_file in category_path.rglob("*.json"):
                try:
                    # Carrega metadata se existir
                    metadata_file = workflow_file.parent / f"{workflow_file.stem}_metadata.json"
                    metadata = {}
                    if metadata_file.exists():
                        with open(metadata_file) as f:
                            metadata = json.load(f)
                    
                    # Carrega workflow para extrair node_map
                    with open(workflow_file) as f:
                        workflow_data = json.load(f)
                        node_map = self._extract_node_map(workflow_data)
                        default_inputs = self._extract_default_inputs(workflow_data)
                    
                    template = WorkflowTemplate(
                        name=workflow_file.stem,
                        description=metadata.get("description", ""),
                        category=category,
                        file_path=workflow_file,
                        metadata=metadata,
                        node_map=node_map,
                        default_inputs=default_inputs
                    )
                    self.templates[template.name] = template
                    logger.info(f"Template {template.name} carregado com sucesso")
                except Exception as e:
                    logger.error(f"Erro ao carregar template {workflow_file}: {e}")
    
    def _extract_node_map(self, workflow: Dict) -> Dict[str, str]:
        """Extrai mapa de nós do workflow."""
        node_map = {}
        for node_id, node in workflow.get("nodes", {}).items():
            if node.get("type") in ["CLIPTextEncode", "KSampler", "VAEDecode"]:
                node_map[node["type"]] = node_id
        return node_map
    
    def _extract_default_inputs(self, workflow: Dict) -> Dict:
        """Extrai inputs padrão do workflow."""
        default_inputs = {}
        for node in workflow.get("nodes", {}).values():
            if "inputs" in node:
                for input_name, value in node["inputs"].items():
                    default_inputs[f"{node['type']}.{input_name}"] = value
        return default_inputs
    
    async def get_template(self, name: str) -> Optional[WorkflowTemplate]:
        """Retorna um template de workflow pelo nome."""
        return self.templates.get(name)
    
    async def list_templates(self, category: Optional[str] = None) -> List[WorkflowTemplate]:
        """Lista todos os templates disponíveis, opcionalmente filtrados por categoria."""
        if category:
            return [t for t in self.templates.values() if t.category == category]
        return list(self.templates.values())
    
    async def load_workflow(self, template_name: str) -> Dict:
        """Carrega um workflow a partir de um template."""
        # Verifica cache primeiro
        if template_name in self.cache:
            return self.cache[template_name].copy()
            
        template = await self.get_template(template_name)
        if not template:
            raise ValueError(f"Template {template_name} não encontrado")
            
        try:
            with open(template.file_path) as f:
                workflow = json.load(f)
            
            # Armazena no cache
            self.cache[template_name] = workflow
            return workflow.copy()
        except Exception as e:
            logger.error(f"Erro ao carregar workflow {template_name}: {e}")
            raise
    
    async def execute_workflow(
        self,
        workflow: Dict,
        inputs: Dict[str, Union[str, int, float, Dict]],
        prompt: Optional[str] = None,
        negative_prompt: Optional[str] = None
    ) -> str:
        """
        Executa um workflow no ComfyUI.
        
        Args:
            workflow: Workflow do ComfyUI em formato JSON
            inputs: Dicionário com os inputs do workflow
            prompt: Prompt positivo opcional
            negative_prompt: Prompt negativo opcional
            
        Returns:
            ID da tarefa no ComfyUI
        """
        # Aplica os inputs no workflow
        if prompt or negative_prompt:
            workflow = self._inject_prompts(
                workflow,
                positive=prompt,
                negative=negative_prompt
            )
        workflow = self._inject_inputs(workflow, inputs)
        
        # Envia para o ComfyUI
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.comfy_api_url}/prompt",
                    json={"prompt": workflow}
                ) as response:
                    result = await response.json()
                    return result["prompt_id"]
        except Exception as e:
            logger.error(f"Erro ao executar workflow: {e}")
            raise
    
    async def get_workflow_status(self, prompt_id: str) -> Dict:
        """Retorna o status de um workflow em execução."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.comfy_api_url}/history/{prompt_id}"
                ) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"Erro ao obter status do workflow {prompt_id}: {e}")
            raise
    
    def _inject_prompts(
        self,
        workflow: Dict,
        positive: Optional[str] = None,
        negative: Optional[str] = None
    ) -> Dict:
        """
        Injeta prompts positivo e negativo no workflow.
        
        Args:
            workflow: Workflow para injetar prompts
            positive: Prompt positivo
            negative: Prompt negativo
            
        Returns:
            Workflow com prompts injetados
        """
        workflow = workflow.copy()
        nodes = workflow.get("nodes", {})
        
        # Injeta prompt positivo
        if positive and "CLIPTextEncode" in workflow["node_map"]:
            pos_node_id = workflow["node_map"]["CLIPTextEncode"]
            if pos_node_id in nodes:
                nodes[pos_node_id]["inputs"]["text"] = positive
                
        # Injeta prompt negativo
        if negative:
            for node in nodes.values():
                if node["type"] == "CLIPTextEncode" and "negative" in node["title"].lower():
                    node["inputs"]["text"] = negative
                    
        return workflow
    
    def _inject_inputs(self, workflow: Dict, inputs: Dict) -> Dict:
        """
        Injeta inputs customizados no workflow.
        
        Args:
            workflow: Workflow para injetar inputs
            inputs: Dicionário com inputs customizados
            
        Returns:
            Workflow com inputs injetados
        """
        workflow = workflow.copy()
        nodes = workflow.get("nodes", {})
        
        for input_key, value in inputs.items():
            # Formato esperado: "node_type.input_name"
            if "." not in input_key:
                continue
                
            node_type, input_name = input_key.split(".")
            if node_type in workflow["node_map"]:
                node_id = workflow["node_map"][node_type]
                if node_id in nodes:
                    nodes[node_id]["inputs"][input_name] = value
                    
        return workflow

# Instância global do gerenciador
workflow_manager = WorkflowManager() 