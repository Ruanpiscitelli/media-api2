"""
Gerenciador de workflows do ComfyUI.
"""
from typing import Dict, Any, List, Optional
import json
from pathlib import Path

from src.comfy.config import ComfyConfig
from src.comfy.workflow_validator import WorkflowValidator

class WorkflowManager:
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
        workflow_path = self.config.get_workflow_path(workflow_name)
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
        workflow_path = self.config.get_workflow_path(workflow_name)
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
        for path in self.config.workflows_dir.glob("*.json"):
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
        workflow_path = self.config.get_workflow_path(workflow_name)
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