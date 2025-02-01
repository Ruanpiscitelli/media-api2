from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class WorkflowExecutionRequest(BaseModel):
    """
    Modelo para requisição de execução de workflow.
    """
    workflow: Dict[str, Any] = Field(
        ...,
        description="Workflow em formato JSON do ComfyUI"
    )
    inputs: Dict[str, Any] = Field(
        ...,
        description="Inputs específicos para o workflow"
    )
    priority: Optional[int] = Field(
        0,
        description="Prioridade da execução (0-10)",
        ge=0,
        le=10
    )

    class Config:
        schema_extra = {
            "example": {
                "workflow": {
                    "1": {
                        "class_type": "KSampler",
                        "inputs": {
                            "seed": 123456789,
                            "steps": 20,
                            "cfg": 7.5,
                            "sampler_name": "euler_ancestral",
                            "scheduler": "karras",
                            "denoise": 1.0,
                            "model": ["4", 0],
                            "positive": ["6", 0],
                            "negative": ["7", 0],
                            "latent_image": ["3", 0]
                        }
                    }
                },
                "inputs": {
                    "prompt": "a beautiful landscape",
                    "negative_prompt": "ugly, blurry"
                },
                "priority": 5
            }
        } 