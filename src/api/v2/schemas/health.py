"""
Schemas Pydantic para o endpoint de health check.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime

class VRAMInfo(BaseModel):
    total: int = Field(..., description="Total de VRAM em MB")
    used: int = Field(..., description="VRAM utilizada em MB")
    free: int = Field(..., description="VRAM livre em MB")

class GPUStatus(BaseModel):
    id: str = Field(..., description="ID da GPU")
    status: str = Field(..., description="Status atual da GPU")
    vram: VRAMInfo = Field(..., description="Informações de VRAM")
    temperature: Optional[float] = Field(None, description="Temperatura em Celsius")
    utilization: Optional[float] = Field(None, description="Porcentagem de utilização")

class ServiceStatus(BaseModel):
    status: str = Field(..., description="Status do serviço (connected, error)")
    error: Optional[str] = Field(None, description="Mensagem de erro se houver")
    latency_ms: Optional[float] = Field(None, description="Latência em milissegundos")

class ComponentsStatus(BaseModel):
    database: ServiceStatus = Field(..., description="Status do banco de dados")
    redis: ServiceStatus = Field(..., description="Status do Redis")
    cache: ServiceStatus = Field(..., description="Status do cache")
    comfyui: Dict = Field(..., description="Status do ComfyUI")

class SystemStatus(BaseModel):
    cpu_usage: float = Field(..., description="Uso de CPU em porcentagem")
    memory_usage: float = Field(..., description="Uso de memória em porcentagem")
    disk_usage: float = Field(..., description="Uso de disco em porcentagem")
    uptime: float = Field(..., description="Tempo de atividade em segundos")

class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Status geral do sistema")
    timestamp: datetime = Field(..., description="Timestamp da verificação")
    components: ComponentsStatus = Field(..., description="Status dos componentes")
    gpus: List[GPUStatus] = Field(..., description="Status das GPUs")
    system: SystemStatus = Field(..., description="Status do sistema")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-03-19T10:00:00Z",
                "components": {
                    "database": {
                        "status": "connected",
                        "latency_ms": 1.5
                    },
                    "redis": {
                        "status": "connected",
                        "used_memory": 1024,
                        "connected_clients": 5
                    },
                    "cache": {
                        "status": "connected"
                    },
                    "comfyui": {
                        "ready": True
                    }
                },
                "gpus": [
                    {
                        "id": "0",
                        "status": "active",
                        "vram": {
                            "total": 24576,
                            "used": 4096,
                            "free": 20480
                        },
                        "temperature": 65.5,
                        "utilization": 45.2
                    }
                ],
                "system": {
                    "cpu_usage": 35.5,
                    "memory_usage": 42.8,
                    "disk_usage": 68.2,
                    "uptime": 86400
                }
            }
        } 