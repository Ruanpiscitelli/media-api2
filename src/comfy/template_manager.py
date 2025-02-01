"""
Gerenciador de templates do ComfyUI.
"""
from typing import Dict, Any, List, Optional, Union
import json
from datetime import datetime
from pathlib import Path
import semver
import copy
import re

from src.api.v2.schemas.templates import (
    TemplateDefinition,
    TemplateMetadata,
    TemplateParameter,
    TemplateVersionInfo
)
from src.comfy.config import ComfyConfig
from src.comfy.workflow_validator import WorkflowValidator

class TemplateManager:
    """
    Gerenciador de templates do ComfyUI.
    
    Responsabilidades:
    - CRUD de templates
    - Versionamento
    - Substituição de parâmetros
    - Validação
    """
    
    def __init__(self):
        self.config = ComfyConfig()
        self.validator = WorkflowValidator()
        
        # Cache de templates
        self._template_cache: Dict[str, TemplateDefinition] = {}
        
        # Regex para substituição de parâmetros
        self._param_regex = re.compile(r"\${([^}]+)}")
        
    def create_template(
        self,
        name: str,
        description: str,
        workflow: Dict[str, Any],
        parameters: Dict[str, TemplateParameter],
        parameter_mappings: Dict[str, List[str]],
        author: str,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None
    ) -> TemplateDefinition:
        """
        Cria um novo template.
        
        Args:
            name: Nome do template
            description: Descrição
            workflow: Workflow base
            parameters: Parâmetros configuráveis
            parameter_mappings: Mapeamento de parâmetros
            author: Autor do template
            tags: Tags para categorização
            category: Categoria
            
        Returns:
            Template criado
            
        Raises:
            ValueError: Se o template já existir ou for inválido
        """
        # Valida nome
        if not self._is_valid_name(name):
            raise ValueError("Nome de template inválido")
            
        template_path = self._get_template_path(name, "1.0.0")
        if template_path.exists():
            raise ValueError(f"Template já existe: {name}")
            
        # Cria template
        template = TemplateDefinition(
            metadata=TemplateMetadata(
                name=name,
                version="1.0.0",
                description=description,
                author=author,
                tags=tags or [],
                category=category
            ),
            parameters=parameters,
            workflow=workflow,
            parameter_mappings=parameter_mappings
        )
        
        # Valida template
        self._validate_template(template)
        
        # Salva no disco
        self._save_template(template)
        
        return template
        
    def get_template(
        self,
        name: str,
        version: Optional[str] = None
    ) -> TemplateDefinition:
        """
        Obtém um template.
        
        Args:
            name: Nome do template
            version: Versão específica (opcional)
            
        Returns:
            Template
            
        Raises:
            FileNotFoundError: Se o template não existir
        """
        # Verifica cache
        cache_key = f"{name}@{version or 'latest'}"
        if cache_key in self._template_cache:
            return self._template_cache[cache_key]
            
        # Obtém versão mais recente se não especificada
        if not version:
            version = self._get_latest_version(name)
            if not version:
                raise FileNotFoundError(f"Template não encontrado: {name}")
                
        # Carrega do disco
        template_path = self._get_template_path(name, version)
        if not template_path.exists():
            raise FileNotFoundError(f"Template não encontrado: {name}@{version}")
            
        with open(template_path, "r") as f:
            template = TemplateDefinition.model_validate_json(f.read())
            
        # Adiciona ao cache
        self._template_cache[cache_key] = template
        
        return template
        
    def update_template(
        self,
        name: str,
        description: Optional[str] = None,
        workflow: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, TemplateParameter]] = None,
        parameter_mappings: Optional[Dict[str, List[str]]] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        author: Optional[str] = None,
        changelog: Optional[str] = None,
        bump_version: Optional[str] = None
    ) -> TemplateDefinition:
        """
        Atualiza um template existente.
        
        Args:
            name: Nome do template
            description: Nova descrição
            workflow: Novo workflow
            parameters: Novos parâmetros
            parameter_mappings: Novo mapeamento
            tags: Novas tags
            category: Nova categoria
            author: Autor da atualização
            changelog: Descrição das mudanças
            bump_version: Tipo de bump de versão (major, minor, patch)
            
        Returns:
            Template atualizado
            
        Raises:
            FileNotFoundError: Se o template não existir
            ValueError: Se a atualização for inválida
        """
        # Carrega template atual
        template = self.get_template(name)
        
        # Cria nova versão
        new_template = copy.deepcopy(template)
        
        # Atualiza campos
        if description:
            new_template.metadata.description = description
        if workflow:
            new_template.workflow = workflow
        if parameters:
            new_template.parameters = parameters
        if parameter_mappings:
            new_template.parameter_mappings = parameter_mappings
        if tags:
            new_template.metadata.tags = tags
        if category:
            new_template.metadata.category = category
            
        # Atualiza versão
        if bump_version:
            current_version = semver.VersionInfo.parse(template.metadata.version)
            if bump_version == "major":
                new_version = current_version.bump_major()
            elif bump_version == "minor":
                new_version = current_version.bump_minor()
            else:
                new_version = current_version.bump_patch()
            new_template.metadata.version = str(new_version)
            
        # Atualiza metadados
        new_template.metadata.updated_at = datetime.utcnow()
        if author:
            new_template.metadata.author = author
            
        # Valida template
        self._validate_template(new_template)
        
        # Salva no disco
        self._save_template(new_template, changelog)
        
        # Atualiza cache
        cache_key = f"{name}@{new_template.metadata.version}"
        self._template_cache[cache_key] = new_template
        self._template_cache[f"{name}@latest"] = new_template
        
        return new_template
        
    def delete_template(self, name: str, version: Optional[str] = None):
        """
        Remove um template.
        
        Args:
            name: Nome do template
            version: Versão específica (opcional)
            
        Raises:
            FileNotFoundError: Se o template não existir
        """
        if version:
            # Remove versão específica
            template_path = self._get_template_path(name, version)
            if not template_path.exists():
                raise FileNotFoundError(f"Template não encontrado: {name}@{version}")
                
            template_path.unlink()
            
            # Remove do cache
            self._template_cache.pop(f"{name}@{version}", None)
            
            # Atualiza latest se necessário
            latest = self._get_latest_version(name)
            if latest:
                latest_template = self.get_template(name, latest)
                self._template_cache[f"{name}@latest"] = latest_template
        else:
            # Remove todas as versões
            template_dir = self._get_template_dir(name)
            if not template_dir.exists():
                raise FileNotFoundError(f"Template não encontrado: {name}")
                
            for path in template_dir.glob("*.json"):
                path.unlink()
            template_dir.rmdir()
            
            # Remove do cache
            for key in list(self._template_cache.keys()):
                if key.startswith(f"{name}@"):
                    self._template_cache.pop(key)
                    
    def list_templates(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 10
    ) -> List[TemplateMetadata]:
        """
        Lista templates disponíveis.
        
        Args:
            category: Filtrar por categoria
            tags: Filtrar por tags
            page: Página atual
            page_size: Tamanho da página
            
        Returns:
            Lista de metadados dos templates
        """
        templates = []
        
        # Lista todos os templates
        templates_dir = self.config.base_dir / "templates"
        if templates_dir.exists():
            for template_dir in templates_dir.iterdir():
                if template_dir.is_dir():
                    try:
                        template = self.get_template(template_dir.name)
                        
                        # Aplica filtros
                        if category and template.metadata.category != category:
                            continue
                            
                        if tags and not all(tag in template.metadata.tags for tag in tags):
                            continue
                            
                        templates.append(template.metadata)
                    except Exception as e:
                        print(f"Erro ao carregar template {template_dir.name}: {e}")
                        
        # Ordena por nome
        templates.sort(key=lambda t: t.name)
        
        # Aplica paginação
        start = (page - 1) * page_size
        end = start + page_size
        
        return templates[start:end]
        
    def get_template_versions(self, name: str) -> List[TemplateVersionInfo]:
        """
        Lista versões de um template.
        
        Args:
            name: Nome do template
            
        Returns:
            Lista de informações das versões
            
        Raises:
            FileNotFoundError: Se o template não existir
        """
        template_dir = self._get_template_dir(name)
        if not template_dir.exists():
            raise FileNotFoundError(f"Template não encontrado: {name}")
            
        versions = []
        for path in template_dir.glob("*.json"):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    versions.append(TemplateVersionInfo(
                        version=data["metadata"]["version"],
                        created_at=datetime.fromisoformat(data["metadata"]["created_at"]),
                        author=data["metadata"]["author"],
                        changelog=data.get("changelog", "")
                    ))
            except Exception as e:
                print(f"Erro ao carregar versão {path}: {e}")
                
        # Ordena por versão
        versions.sort(key=lambda v: semver.VersionInfo.parse(v.version), reverse=True)
        
        return versions
        
    def apply_parameters(
        self,
        template: TemplateDefinition,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Aplica parâmetros em um template.
        
        Args:
            template: Template
            parameters: Valores dos parâmetros
            
        Returns:
            Workflow com parâmetros aplicados
            
        Raises:
            ValueError: Se os parâmetros forem inválidos
        """
        # Valida parâmetros
        self._validate_parameters(template, parameters)
        
        # Cria cópia do workflow
        workflow = copy.deepcopy(template.workflow)
        
        # Aplica parâmetros
        for param_name, param_value in parameters.items():
            if param_name not in template.parameter_mappings:
                continue
                
            # Obtém mapeamentos do parâmetro
            mappings = template.parameter_mappings[param_name]
            
            for mapping in mappings:
                # Formato: node_id.input_name[.field]
                parts = mapping.split(".")
                node_id = parts[0]
                input_name = parts[1]
                field = parts[2] if len(parts) > 2 else None
                
                if node_id not in workflow["nodes"]:
                    continue
                    
                node = workflow["nodes"][node_id]
                if input_name not in node["inputs"]:
                    continue
                    
                if field:
                    # Atualiza campo específico
                    node["inputs"][input_name][field] = param_value
                else:
                    # Atualiza input inteiro
                    node["inputs"][input_name] = param_value
                    
        return workflow
        
    def _validate_template(self, template: TemplateDefinition):
        """
        Valida um template.
        
        Args:
            template: Template para validar
            
        Raises:
            ValueError: Se o template for inválido
        """
        # Valida workflow
        self.validator.validate(template.workflow)
        
        # Valida mapeamentos
        for param_name, mappings in template.parameter_mappings.items():
            if param_name not in template.parameters:
                raise ValueError(f"Parâmetro não definido: {param_name}")
                
            for mapping in mappings:
                parts = mapping.split(".")
                if len(parts) < 2:
                    raise ValueError(f"Mapeamento inválido: {mapping}")
                    
                node_id = parts[0]
                input_name = parts[1]
                
                if node_id not in template.workflow["nodes"]:
                    raise ValueError(f"Nó não encontrado: {node_id}")
                    
                node = template.workflow["nodes"][node_id]
                if input_name not in node["inputs"]:
                    raise ValueError(f"Input não encontrado: {node_id}.{input_name}")
                    
    def _validate_parameters(
        self,
        template: TemplateDefinition,
        parameters: Dict[str, Any]
    ):
        """
        Valida parâmetros para um template.
        
        Args:
            template: Template
            parameters: Parâmetros para validar
            
        Raises:
            ValueError: Se os parâmetros forem inválidos
        """
        # Verifica parâmetros obrigatórios
        for name, param in template.parameters.items():
            if param.required and name not in parameters:
                raise ValueError(f"Parâmetro obrigatório não fornecido: {name}")
                
        # Valida cada parâmetro
        for name, value in parameters.items():
            if name not in template.parameters:
                raise ValueError(f"Parâmetro desconhecido: {name}")
                
            param = template.parameters[name]
            
            # Valida tipo
            if not self._validate_parameter_type(value, param):
                raise ValueError(
                    f"Tipo inválido para parâmetro {name}. "
                    f"Esperado {param.type}, recebido {type(value)}"
                )
                
            # Valida range numérico
            if param.type in ("integer", "float"):
                if param.min_value is not None and value < param.min_value:
                    raise ValueError(
                        f"Valor muito baixo para parâmetro {name}. "
                        f"Mínimo: {param.min_value}"
                    )
                if param.max_value is not None and value > param.max_value:
                    raise ValueError(
                        f"Valor muito alto para parâmetro {name}. "
                        f"Máximo: {param.max_value}"
                    )
                    
            # Valida enum
            if param.type == "enum" and param.enum_values:
                if value not in param.enum_values:
                    raise ValueError(
                        f"Valor inválido para parâmetro {name}. "
                        f"Valores possíveis: {param.enum_values}"
                    )
                    
    def _validate_parameter_type(
        self,
        value: Any,
        parameter: TemplateParameter
    ) -> bool:
        """
        Valida o tipo de um valor de parâmetro.
        
        Args:
            value: Valor para validar
            parameter: Definição do parâmetro
            
        Returns:
            True se o tipo for válido
        """
        if parameter.type == "string":
            return isinstance(value, str)
        elif parameter.type == "integer":
            return isinstance(value, int)
        elif parameter.type == "float":
            return isinstance(value, (int, float))
        elif parameter.type == "boolean":
            return isinstance(value, bool)
        elif parameter.type == "enum":
            return isinstance(value, str)
        elif parameter.type in ("image", "model", "lora", "embedding"):
            return isinstance(value, str)
        return True
        
    def _get_template_dir(self, name: str) -> Path:
        """Retorna diretório de um template."""
        return self.config.base_dir / "templates" / name
        
    def _get_template_path(self, name: str, version: str) -> Path:
        """Retorna caminho para um template específico."""
        return self._get_template_dir(name) / f"{version}.json"
        
    def _get_latest_version(self, name: str) -> Optional[str]:
        """Retorna versão mais recente de um template."""
        template_dir = self._get_template_dir(name)
        if not template_dir.exists():
            return None
            
        versions = []
        for path in template_dir.glob("*.json"):
            try:
                version = path.stem
                versions.append(semver.VersionInfo.parse(version))
            except ValueError:
                continue
                
        if not versions:
            return None
            
        return str(max(versions))
        
    def _is_valid_name(self, name: str) -> bool:
        """Valida nome de template."""
        return bool(re.match(r"^[a-zA-Z0-9_-]+$", name)) 