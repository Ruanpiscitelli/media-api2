"""
Endpoints para monitoramento do sistema.
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import asyncio
import torch
from sqlalchemy.ext.asyncio import AsyncSessionLocal
from sqlalchemy import text

from src.core.config import settings
from src.services.auth import get_current_admin_user
from src.services.monitoring import MonitoringService
from src.services.gpu_manager import GPUManager
from src.services.redis import redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

# Schemas
class SystemMetrics(BaseModel):
    """Métricas do sistema."""
    cpu_usage: float = Field(..., description="Uso de CPU em porcentagem")
    memory_usage: Dict[str, float] = Field(..., description="Uso de memória RAM")
    disk_usage: Dict[str, float] = Field(..., description="Uso de disco")
    network_io: Dict[str, float] = Field(..., description="I/O de rede")
    uptime: float = Field(..., description="Tempo de atividade em segundos")
    process_count: int = Field(..., description="Número de processos")

class GPUMetrics(BaseModel):
    """Métricas de GPU."""
    id: str = Field(..., description="ID da GPU")
    name: str = Field(..., description="Nome da GPU")
    temperature: float = Field(..., description="Temperatura em Celsius")
    power_usage: float = Field(..., description="Uso de energia em Watts")
    memory_used: float = Field(..., description="Memória usada em MB")
    memory_total: float = Field(..., description="Memória total em MB")
    utilization: float = Field(..., description="Utilização em porcentagem")
    processes: List[Dict[str, Any]] = Field(..., description="Processos em execução")

class APIMetrics(BaseModel):
    """Métricas da API."""
    requests_total: int = Field(..., description="Total de requisições")
    requests_per_endpoint: Dict[str, int] = Field(..., description="Requisições por endpoint")
    average_response_time: float = Field(..., description="Tempo médio de resposta em ms")
    error_count: int = Field(..., description="Total de erros")
    active_users: int = Field(..., description="Usuários ativos")

class JobMetrics(BaseModel):
    """Métricas de jobs."""
    total_jobs: int = Field(..., description="Total de jobs")
    active_jobs: int = Field(..., description="Jobs ativos")
    completed_jobs: int = Field(..., description="Jobs concluídos")
    failed_jobs: int = Field(..., description="Jobs com falha")
    average_processing_time: float = Field(..., description="Tempo médio de processamento em segundos")
    queue_size: int = Field(..., description="Tamanho da fila")

class AlertConfig(BaseModel):
    """Configuração de alerta."""
    metric: str = Field(..., description="Métrica monitorada")
    condition: str = Field(..., description="Condição do alerta (>, <, =)")
    threshold: float = Field(..., description="Valor limite")
    duration: int = Field(..., description="Duração em segundos")
    severity: str = Field(..., description="Severidade (low, medium, high)")
    enabled: bool = Field(default=True, description="Se o alerta está ativo")

# Endpoints
@router.get("/system", response_model=SystemMetrics)
async def get_system_metrics(
    current_user = Depends(get_current_admin_user)
):
    """
    Obtém métricas do sistema (apenas admin).
    """
    try:
        monitoring = MonitoringService()
        metrics = await monitoring.get_system_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"Erro obtendo métricas do sistema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gpu", response_model=List[GPUMetrics])
async def get_gpu_metrics(
    current_user = Depends(get_current_admin_user)
):
    """
    Obtém métricas das GPUs (apenas admin).
    """
    try:
        gpu_manager = GPUManager()
        metrics = await gpu_manager.get_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"Erro obtendo métricas das GPUs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api", response_model=APIMetrics)
async def get_api_metrics(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    current_user = Depends(get_current_admin_user)
):
    """
    Obtém métricas da API (apenas admin).
    """
    try:
        monitoring = MonitoringService()
        
        # Usar últimas 24h se não especificado
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=1)
        if not end_time:
            end_time = datetime.utcnow()
            
        metrics = await monitoring.get_api_metrics(
            start_time=start_time,
            end_time=end_time
        )
        return metrics
        
    except Exception as e:
        logger.error(f"Erro obtendo métricas da API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs", response_model=JobMetrics)
async def get_job_metrics(
    job_type: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    current_user = Depends(get_current_admin_user)
):
    """
    Obtém métricas dos jobs (apenas admin).
    """
    try:
        monitoring = MonitoringService()
        
        # Usar últimas 24h se não especificado
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=1)
        if not end_time:
            end_time = datetime.utcnow()
            
        metrics = await monitoring.get_job_metrics(
            job_type=job_type,
            start_time=start_time,
            end_time=end_time
        )
        return metrics
        
    except Exception as e:
        logger.error(f"Erro obtendo métricas dos jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts", response_model=List[AlertConfig])
async def list_alerts(
    current_user = Depends(get_current_admin_user)
):
    """
    Lista configurações de alertas (apenas admin).
    """
    try:
        monitoring = MonitoringService()
        alerts = await monitoring.list_alerts()
        return alerts
        
    except Exception as e:
        logger.error(f"Erro listando alertas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts")
async def create_alert(
    alert_config: AlertConfig,
    current_user = Depends(get_current_admin_user)
):
    """
    Cria nova configuração de alerta (apenas admin).
    """
    try:
        monitoring = MonitoringService()
        await monitoring.create_alert(alert_config)
        
        return {
            "status": "success",
            "message": "Alerta criado com sucesso"
        }
        
    except Exception as e:
        logger.error(f"Erro criando alerta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/alerts/{alert_id}")
async def update_alert(
    alert_id: str,
    alert_config: AlertConfig,
    current_user = Depends(get_current_admin_user)
):
    """
    Atualiza configuração de alerta (apenas admin).
    """
    try:
        monitoring = MonitoringService()
        
        # Verificar se alerta existe
        if not await monitoring.alert_exists(alert_id):
            raise HTTPException(
                status_code=404,
                detail="Alerta não encontrado"
            )
            
        await monitoring.update_alert(alert_id, alert_config)
        
        return {
            "status": "success",
            "message": "Alerta atualizado com sucesso"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro atualizando alerta {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: str,
    current_user = Depends(get_current_admin_user)
):
    """
    Remove configuração de alerta (apenas admin).
    """
    try:
        monitoring = MonitoringService()
        
        # Verificar se alerta existe
        if not await monitoring.alert_exists(alert_id):
            raise HTTPException(
                status_code=404,
                detail="Alerta não encontrado"
            )
            
        await monitoring.delete_alert(alert_id)
        
        return {
            "status": "success",
            "message": "Alerta removido com sucesso"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro removendo alerta {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs")
async def get_system_logs(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    level: Optional[str] = None,
    service: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    current_user = Depends(get_current_admin_user)
):
    """
    Obtém logs do sistema (apenas admin).
    """
    try:
        monitoring = MonitoringService()
        
        # Usar últimas 24h se não especificado
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=1)
        if not end_time:
            end_time = datetime.utcnow()
            
        logs = await monitoring.get_system_logs(
            start_time=start_time,
            end_time=end_time,
            level=level,
            service=service,
            limit=limit
        )
        
        return {
            "logs": logs,
            "total": len(logs)
        }
        
    except Exception as e:
        logger.error(f"Erro obtendo logs do sistema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """
    Verificação de saúde mais robusta
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "services": {}
    }
    
    # Verificar Redis
    try:
        await redis_client.ping()
        health["services"]["redis"] = "healthy"
    except Exception as e:
        health["services"]["redis"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"
    
    # Verificar Banco de Dados
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        health["services"]["database"] = "healthy"
    except Exception as e:
        health["services"]["database"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"
    
    # Verificar GPU se necessário
    if torch.cuda.is_available():
        try:
            torch.cuda.memory_summary()
            health["services"]["gpu"] = "healthy"
        except Exception as e:
            health["services"]["gpu"] = f"unhealthy: {str(e)}"
            health["status"] = "degraded"
    
    return health 