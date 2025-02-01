"""
Sistema de templates para ComfyUI.
Gerencia templates predefinidos e suas modificações.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class TemplateModification(BaseModel):
    """Modelo para modificações de template"""
    sampler: Dict[str, Union[int, float]] = Field(
        default_factory=lambda: {
            "steps": 30,
            "cfg": 7.0,
            "scheduler": "DPMSolverMultistepScheduler"
        }
    )
    size: Dict[str, int] = Field(
        default_factory=lambda: {
            "width": 1024,
            "height": 1024
        }
    )
    style: Optional[Dict[str, Union[str, float]]] = None
    lora: Optional[Dict[str, float]] = None
    post_processing: Optional[Dict[str, Union[bool, float]]] = None

class TemplateConfig(BaseModel):
    """Modelo para configuração de template"""
    base: str
    modifications: TemplateModification
    description: str = ""
    category: str = "general"
    metadata: Dict = {}

class TemplateSystem:
    """Sistema de templates para ComfyUI"""
    
    def __init__(self, templates_dir: Union[str, Path] = "workflows/templates"):
        """Inicializa o sistema de templates"""
        self.templates_dir = Path(templates_dir)
        self.templates: Dict[str, TemplateConfig] = {}
        self._load_default_templates()
        
    def _load_default_templates(self):
        """Carrega templates padrão"""
        self.templates = {
            "portrait": TemplateConfig(
                base="sdxl_base",
                description="Template otimizado para retratos",
                category="portraits",
                modifications=TemplateModification(
                    sampler={
                        "steps": 30,
                        "cfg": 7.0,
                        "scheduler": "DPMSolverMultistepScheduler"
                    },
                    size={
                        "width": 768,
                        "height": 1024
                    },
                    style={
                        "style_text": "professional portrait photography, studio lighting",
                        "weight": 1.2
                    },
                    post_processing={
                        "face_enhance": True,
                        "skin_retouch": 0.3,
                        "sharpness": 1.1
                    }
                )
            ),
            "landscape": TemplateConfig(
                base="sdxl_base",
                description="Template otimizado para paisagens",
                category="landscapes",
                modifications=TemplateModification(
                    sampler={
                        "steps": 35,
                        "cfg": 8.0,
                        "scheduler": "DPMSolverMultistepScheduler"
                    },
                    size={
                        "width": 1024,
                        "height": 768
                    },
                    style={
                        "style_text": "professional landscape photography, golden hour",
                        "weight": 1.3
                    },
                    post_processing={
                        "enhance_detail": True,
                        "vibrance": 1.2,
                        "sharpness": 1.1
                    }
                )
            ),
            "anime": TemplateConfig(
                base="sdxl_base",
                description="Template otimizado para estilo anime",
                category="anime",
                modifications=TemplateModification(
                    sampler={
                        "steps": 28,
                        "cfg": 7.0,
                        "scheduler": "DPMSolverMultistepScheduler"
                    },
                    size={
                        "width": 1024,
                        "height": 1024
                    },
                    style={
                        "style_text": "anime style, detailed linework",
                        "weight": 1.2
                    },
                    lora={
                        "anime_style_v1": 0.8
                    }
                )
            )
        }
        
    def load_template(self, name: str) -> Optional[TemplateConfig]:
        """Carrega um template pelo nome"""
        if name in self.templates:
            return self.templates[name]
            
        # Tenta carregar do arquivo
        template_path = self.templates_dir / f"{name}.json"
        if template_path.exists():
            try:
                with open(template_path) as f:
                    data = json.load(f)
                    config = TemplateConfig(**data)
                    self.templates[name] = config
                    return config
            except Exception as e:
                logger.error(f"Erro ao carregar template {name}: {e}")
                
        return None
        
    def list_templates(
        self,
        category: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Lista templates disponíveis"""
        templates = []
        for name, config in self.templates.items():
            if not category or config.category == category:
                templates.append({
                    "name": name,
                    "description": config.description,
                    "category": config.category
                })
        return templates
        
    def apply_template(
        self,
        workflow: Dict,
        template_name: str
    ) -> Dict:
        """Aplica um template a um workflow"""
        template = self.load_template(template_name)
        if not template:
            raise ValueError(f"Template {template_name} não encontrado")
            
        workflow = workflow.copy()
        
        # Aplicar modificações do template
        self._apply_sampler_config(workflow, template.modifications.sampler)
        self._apply_size_config(workflow, template.modifications.size)
        
        if template.modifications.style:
            self._apply_style_config(workflow, template.modifications.style)
            
        if template.modifications.lora:
            self._apply_lora_config(workflow, template.modifications.lora)
            
        if template.modifications.post_processing:
            self._apply_post_processing(workflow, template.modifications.post_processing)
            
        return workflow
        
    def _apply_sampler_config(
        self,
        workflow: Dict,
        config: Dict[str, Union[int, float]]
    ):
        """Aplica configurações do sampler"""
        for node in workflow.get("nodes", {}).values():
            if node["type"] == "KSampler":
                node["inputs"].update({
                    "steps": config["steps"],
                    "cfg": config["cfg"],
                    "scheduler": config["scheduler"]
                })
                
    def _apply_size_config(
        self,
        workflow: Dict,
        config: Dict[str, int]
    ):
        """Aplica configurações de tamanho"""
        for node in workflow.get("nodes", {}).values():
            if node["type"] == "EmptyLatentImage":
                node["inputs"].update({
                    "width": config["width"],
                    "height": config["height"]
                })
                
    def _apply_style_config(
        self,
        workflow: Dict,
        config: Dict[str, Union[str, float]]
    ):
        """Aplica configurações de estilo"""
        for node in workflow.get("nodes", {}).values():
            if node["type"] == "StyleProcessor":
                node["inputs"].update({
                    "style_text": config["style_text"],
                    "weight": config["weight"]
                })
                
    def _apply_lora_config(
        self,
        workflow: Dict,
        config: Dict[str, float]
    ):
        """Aplica configurações de LoRA"""
        for node in workflow.get("nodes", {}).values():
            if node["type"] == "LoraLoader":
                for lora_name, strength in config.items():
                    node["inputs"].update({
                        "lora_name": lora_name,
                        "strength": strength
                    })
                    
    def _apply_post_processing(
        self,
        workflow: Dict,
        config: Dict[str, Union[bool, float]]
    ):
        """Aplica configurações de pós-processamento"""
        for node in workflow.get("nodes", {}).values():
            if node["type"] == "ImageProcessor":
                node["inputs"].update({
                    k: v for k, v in config.items()
                    if k in ["sharpness", "vibrance"]
                })
            elif node["type"] == "FaceEnhancer" and config.get("face_enhance"):
                node["inputs"]["strength"] = config.get("skin_retouch", 0.3)

# Instância global do sistema de templates
template_system = TemplateSystem() 