"""
Validador de workflows do ComfyUI.
"""
from typing import Dict, Any, List, Set
import json

from src.comfy.client import ComfyClient

class WorkflowValidator:
    """
    Validador de workflows do ComfyUI.
    
    Responsabilidades:
    - Validar estrutura do workflow
    - Validar nós e conexões
    - Validar tipos de dados
    - Detectar ciclos
    """
    
    def __init__(self):
        self.client = ComfyClient()
        
        # Cache de informações dos nós
        self._node_info: Dict[str, Any] = {}
        
    async def validate(self, workflow: Dict[str, Any]) -> bool:
        """
        Valida um workflow completo.
        
        Args:
            workflow: Workflow em formato JSON
            
        Returns:
            True se válido
            
        Raises:
            ValueError: Se o workflow for inválido
        """
        # Valida estrutura básica
        if not isinstance(workflow, dict):
            raise ValueError("Workflow deve ser um dicionário")
            
        if "nodes" not in workflow:
            raise ValueError("Workflow deve ter uma chave 'nodes'")
            
        if not isinstance(workflow["nodes"], dict):
            raise ValueError("'nodes' deve ser um dicionário")
            
        # Carrega informações dos nós se necessário
        if not self._node_info:
            self._node_info = await self.client.get_object_info()
            
        # Valida cada nó
        for node_id, node in workflow["nodes"].items():
            self._validate_node(node_id, node)
            
        # Valida conexões
        self._validate_connections(workflow["nodes"])
        
        # Detecta ciclos
        if self._has_cycles(workflow["nodes"]):
            raise ValueError("Workflow contém ciclos")
            
        return True
        
    def _validate_node(self, node_id: str, node: Dict[str, Any]):
        """
        Valida um nó individual.
        
        Args:
            node_id: ID do nó
            node: Dados do nó
            
        Raises:
            ValueError: Se o nó for inválido
        """
        # Valida estrutura básica do nó
        required_fields = {"class_type", "inputs"}
        missing_fields = required_fields - set(node.keys())
        if missing_fields:
            raise ValueError(f"Nó {node_id} está faltando campos: {missing_fields}")
            
        # Valida tipo do nó
        class_type = node["class_type"]
        if class_type not in self._node_info:
            raise ValueError(f"Tipo de nó desconhecido: {class_type}")
            
        # Valida inputs
        node_info = self._node_info[class_type]
        self._validate_node_inputs(node_id, node["inputs"], node_info["inputs"])
        
    def _validate_node_inputs(
        self,
        node_id: str,
        inputs: Dict[str, Any],
        input_info: Dict[str, Any]
    ):
        """
        Valida os inputs de um nó.
        
        Args:
            node_id: ID do nó
            inputs: Inputs do nó
            input_info: Informações sobre inputs válidos
            
        Raises:
            ValueError: Se os inputs forem inválidos
        """
        # Verifica inputs obrigatórios
        for input_name, info in input_info.items():
            if info.get("required", False) and input_name not in inputs:
                raise ValueError(f"Input obrigatório '{input_name}' faltando no nó {node_id}")
                
        # Valida cada input
        for input_name, value in inputs.items():
            if input_name not in input_info:
                raise ValueError(f"Input desconhecido '{input_name}' no nó {node_id}")
                
            info = input_info[input_name]
            
            # Valida tipo do input
            if not self._validate_input_type(value, info["type"]):
                raise ValueError(
                    f"Tipo inválido para input '{input_name}' no nó {node_id}. "
                    f"Esperado {info['type']}, recebido {type(value)}"
                )
                
    def _validate_input_type(self, value: Any, expected_type: str) -> bool:
        """
        Valida o tipo de um input.
        
        Args:
            value: Valor do input
            expected_type: Tipo esperado
            
        Returns:
            True se o tipo for válido
        """
        # TODO: Implementar validação de tipos mais complexa
        # Por enquanto aceita qualquer tipo
        return True
        
    def _validate_connections(self, nodes: Dict[str, Any]):
        """
        Valida as conexões entre nós.
        
        Args:
            nodes: Nós do workflow
            
        Raises:
            ValueError: Se as conexões forem inválidas
        """
        # Coleta todos os node_ids
        node_ids = set(nodes.keys())
        
        # Verifica cada conexão
        for node_id, node in nodes.items():
            for input_name, input_value in node["inputs"].items():
                if isinstance(input_value, list) and len(input_value) == 2:
                    # É uma conexão [node_id, output_name]
                    source_id, output_name = input_value
                    
                    # Valida node_id fonte
                    if source_id not in node_ids:
                        raise ValueError(
                            f"Conexão inválida no nó {node_id}: "
                            f"nó fonte {source_id} não existe"
                        )
                        
                    # Valida output
                    source_node = nodes[source_id]
                    if "outputs" not in source_node:
                        raise ValueError(
                            f"Conexão inválida no nó {node_id}: "
                            f"nó fonte {source_id} não tem outputs"
                        )
                        
                    source_outputs = source_node["outputs"]
                    if output_name not in source_outputs:
                        raise ValueError(
                            f"Conexão inválida no nó {node_id}: "
                            f"output '{output_name}' não existe no nó {source_id}"
                        )
                        
    def _has_cycles(self, nodes: Dict[str, Any]) -> bool:
        """
        Detecta ciclos no workflow.
        
        Args:
            nodes: Nós do workflow
            
        Returns:
            True se houver ciclos
        """
        # Constrói grafo de dependências
        graph: Dict[str, Set[str]] = {}
        for node_id, node in nodes.items():
            graph[node_id] = set()
            for input_value in node["inputs"].values():
                if isinstance(input_value, list) and len(input_value) == 2:
                    source_id = input_value[0]
                    graph[node_id].add(source_id)
                    
        # Detecta ciclos usando DFS
        visited = set()
        path = set()
        
        def has_cycle(node_id: str) -> bool:
            if node_id in path:
                return True
                
            if node_id in visited:
                return False
                
            visited.add(node_id)
            path.add(node_id)
            
            for neighbor in graph[node_id]:
                if has_cycle(neighbor):
                    return True
                    
            path.remove(node_id)
            return False
            
        # Verifica cada nó
        for node_id in nodes:
            if node_id not in visited:
                if has_cycle(node_id):
                    return True
                    
        return False 