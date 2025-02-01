"""
Gerenciador de LoRAs para SDXL.
Responsável por carregar, gerenciar e aplicar adaptadores LoRA.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
import torch
from torch import nn
from safetensors.torch import load_file

from src.core.config import settings
from src.core.exceptions import LoraError

logger = logging.getLogger(__name__)

class LoraConfig:
    """Configuração para um adaptador LoRA."""
    def __init__(
        self,
        name: str,
        path: Path,
        metadata: Dict = None,
        compatibility: List[str] = None
    ):
        self.name = name
        self.path = path
        self.metadata = metadata or {}
        self.compatibility = compatibility or []
        self.is_loaded = False
        self.model = None
        
class LoraManager:
    """
    Gerenciador de adaptadores LoRA.
    Implementa carregamento dinâmico e verificação de compatibilidade.
    """
    
    def __init__(self, lora_path: str = None):
        """
        Inicializa o gerenciador de LoRAs.
        
        Args:
            lora_path: Caminho base para os adaptadores LoRA
        """
        self.lora_path = Path(lora_path or settings.LORA_PATH)
        self.loras: Dict[str, LoraConfig] = {}
        self.loaded_loras: Dict[str, Dict] = {}
        self.compatibility_matrix = self._load_compatibility()
        
    def _load_compatibility(self) -> Dict:
        """
        Carrega matriz de compatibilidade entre LoRAs.
        """
        try:
            compat_file = self.lora_path / "compatibility.json"
            if compat_file.exists():
                with open(compat_file) as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Erro carregando matriz de compatibilidade: {e}")
            return {}
            
    async def scan_loras(self) -> None:
        """Escaneia e registra LoRAs disponíveis."""
        try:
            for lora_file in self.lora_path.rglob("*.safetensors"):
                name = lora_file.stem
                
                # Carrega metadata se existir
                metadata_file = lora_file.parent / f"{name}_metadata.json"
                metadata = {}
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                        
                # Verifica compatibilidade
                compatibility = self.compatibility_matrix.get(name, [])
                
                self.loras[name] = LoraConfig(
                    name=name,
                    path=lora_file,
                    metadata=metadata,
                    compatibility=compatibility
                )
                
                logger.info(f"LoRA {name} registrada com sucesso")
                
        except Exception as e:
            logger.error(f"Erro escaneando LoRAs: {e}")
            raise LoraError(f"Falha ao escanear LoRAs: {e}")
            
    async def load_lora(
        self,
        name: str,
        device: str = "cuda"
    ) -> Optional[Dict]:
        """
        Carrega um adaptador LoRA.
        
        Args:
            name: Nome do adaptador
            device: Dispositivo para carregar ('cuda' ou 'cpu')
            
        Returns:
            Dicionário com estado do adaptador
        """
        try:
            # Verifica se já está carregado
            if name in self.loaded_loras:
                return self.loaded_loras[name]
                
            # Verifica se existe
            if name not in self.loras:
                raise LoraError(f"LoRA {name} não encontrada")
                
            lora = self.loras[name]
            
            # Carrega modelo
            state_dict = load_file(
                lora.path,
                device=device
            )
            
            self.loaded_loras[name] = {
                'state_dict': state_dict,
                'config': lora
            }
            
            lora.is_loaded = True
            logger.info(f"LoRA {name} carregada com sucesso")
            
            return self.loaded_loras[name]
            
        except Exception as e:
            logger.error(f"Erro carregando LoRA {name}: {e}")
            raise LoraError(f"Falha ao carregar LoRA: {e}")
            
    def check_compatibility(
        self,
        loras: List[Dict[str, float]]
    ) -> bool:
        """
        Verifica compatibilidade entre múltiplas LoRAs.
        
        Args:
            loras: Lista de dicionários com nome e peso das LoRAs
            
        Returns:
            True se compatíveis, False caso contrário
        """
        try:
            lora_names = [list(lora.keys())[0] for lora in loras]
            
            # Verifica cada par
            for i, name1 in enumerate(lora_names):
                for name2 in lora_names[i+1:]:
                    if name2 not in self.loras[name1].compatibility:
                        logger.warning(
                            f"LoRAs {name1} e {name2} não são compatíveis"
                        )
                        return False
                        
            return True
            
        except Exception as e:
            logger.error(f"Erro verificando compatibilidade: {e}")
            return False
            
    async def apply_loras(
        self,
        model: nn.Module,
        loras: List[Dict[str, float]]
    ) -> nn.Module:
        """
        Aplica múltiplas LoRAs ao modelo.
        
        Args:
            model: Modelo base
            loras: Lista de dicionários com nome e peso das LoRAs
            
        Returns:
            Modelo com LoRAs aplicadas
        """
        try:
            # Verifica compatibilidade
            if not self.check_compatibility(loras):
                raise LoraError("LoRAs incompatíveis")
                
            # Carrega e aplica cada LoRA
            for lora_config in loras:
                for name, weight in lora_config.items():
                    # Carrega se necessário
                    if name not in self.loaded_loras:
                        await self.load_lora(name)
                        
                    # Aplica ao modelo
                    model = self._apply_single_lora(
                        model,
                        self.loaded_loras[name]['state_dict'],
                        weight
                    )
                    
            return model
            
        except Exception as e:
            logger.error(f"Erro aplicando LoRAs: {e}")
            raise LoraError(f"Falha ao aplicar LoRAs: {e}")
            
    def _apply_single_lora(
        self,
        model: nn.Module,
        state_dict: Dict[str, torch.Tensor],
        weight: float = 1.0
    ) -> nn.Module:
        """
        Aplica uma única LoRA ao modelo.
        
        Args:
            model: Modelo base
            state_dict: Estado da LoRA
            weight: Peso para aplicação
            
        Returns:
            Modelo com LoRA aplicada
        """
        try:
            with torch.no_grad():
                for key, value in state_dict.items():
                    if "lora" in key.lower():
                        target_key = key.replace("lora_", "")
                        if hasattr(model, target_key):
                            target = getattr(model, target_key)
                            target.data += value * weight
                            
            return model
            
        except Exception as e:
            logger.error(f"Erro aplicando LoRA: {e}")
            raise LoraError(f"Falha ao aplicar LoRA: {e}")
            
    def get_lora_info(self, name: str) -> Optional[Dict]:
        """
        Retorna informações sobre uma LoRA.
        
        Args:
            name: Nome da LoRA
            
        Returns:
            Dicionário com informações da LoRA
        """
        if name not in self.loras:
            return None
            
        lora = self.loras[name]
        return {
            'name': lora.name,
            'metadata': lora.metadata,
            'compatibility': lora.compatibility,
            'is_loaded': lora.is_loaded
        }
        
    def list_loras(
        self,
        filter_loaded: bool = False
    ) -> List[Dict]:
        """
        Lista todas as LoRAs disponíveis.
        
        Args:
            filter_loaded: Se True, retorna apenas LoRAs carregadas
            
        Returns:
            Lista de informações das LoRAs
        """
        loras = []
        for name, lora in self.loras.items():
            if not filter_loaded or lora.is_loaded:
                loras.append(self.get_lora_info(name))
        return loras
        
    def unload_lora(self, name: str) -> None:
        """
        Descarrega uma LoRA da memória.
        
        Args:
            name: Nome da LoRA
        """
        if name in self.loaded_loras:
            del self.loaded_loras[name]
            if name in self.loras:
                self.loras[name].is_loaded = False
            logger.info(f"LoRA {name} descarregada")
            
    def clear_loaded_loras(self) -> None:
        """Descarrega todas as LoRAs carregadas."""
        self.loaded_loras.clear()
        for lora in self.loras.values():
            lora.is_loaded = False
        logger.info("Todas as LoRAs foram descarregadas") 