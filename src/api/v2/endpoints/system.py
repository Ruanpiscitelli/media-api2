"""
Endpoints para monitoramento e gerenciamento do sistema.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
from src.core.auth import get_current_user, get_admin_user
from src.services.system import SystemService
from src.services.monitoring import MonitoringService
from src.services.queue import QueueService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

system_service = SystemService()
monitoring_service = MonitoringService()
queue_service = QueueService()

class SystemStatus(BaseModel):
    """Modelo para status do sistema"""
    status: str
    gpu_usage: Dict[str, float]
    queue_size: int
    active_workers: int
    uptime: float

class QueueStatus(BaseModel):
    """Modelo para status das filas"""
    high_priority: int
    normal: int
    batch: int
    total_tasks: int

@router.get("/status", response_model=SystemStatus)
async def system_status():
    """Retorna o status do sistema"""
    try:
        status = await system_service.get_status()
        return {
            "status": "online",
            "gpu_usage": status["gpu_usage"],
            "queue_size": status["queue_size"],
            "active_workers": status["active_workers"],
            "uptime": status["uptime"]
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter status do sistema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def system_metrics(
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    current_user = Depends(get_admin_user)
):
    """Retorna métricas detalhadas do sistema"""
    try:
        metrics = await monitoring_service.get_metrics(
            start_time=start_time,
            end_time=end_time
        )
        return {"metrics": metrics}
        
    except Exception as e:
        logger.error(f"Erro ao obter métricas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue", response_model=QueueStatus)
async def queue_status(
    current_user = Depends(get_admin_user)
):
    """Retorna status das filas de processamento"""
    try:
        queues = await queue_service.get_status()
        return {
            "high_priority": queues["high_priority"],
            "normal": queues["normal"],
            "batch": queues["batch"],
            "total_tasks": queues["total_tasks"]
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter status das filas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gpu/status")
async def gpu_status(
    current_user = Depends(get_admin_user)
):
    """Retorna status detalhado das GPUs"""
    try:
        status = await system_service.get_gpu_status()
        return {"gpus": status}
        
    except Exception as e:
        logger.error(f"Erro ao obter status das GPUs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/maintenance/start")
async def start_maintenance(
    current_user = Depends(get_admin_user)
):
    """Inicia modo de manutenção"""
    try:
        await system_service.start_maintenance()
        return {"status": "maintenance_started"}
        
    except Exception as e:
        logger.error(f"Erro ao iniciar manutenção: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/maintenance/stop")
async def stop_maintenance(
    current_user = Depends(get_admin_user)
):
    """Finaliza modo de manutenção"""
    try:
        await system_service.stop_maintenance()
        return {"status": "maintenance_stopped"}
        
    except Exception as e:
        logger.error(f"Erro ao finalizar manutenção: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs")
async def system_logs(
    level: Optional[str] = None,
    service: Optional[str] = None,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = 100,
    current_user = Depends(get_admin_user)
):
    """Retorna logs do sistema"""
    try:
        logs = await monitoring_service.get_logs(
            level=level,
            service=service,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        return {"logs": logs}
        
    except Exception as e:
        logger.error(f"Erro ao obter logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/active")
async def active_tasks(
    current_user = Depends(get_admin_user)
):
    """Lista tarefas em execução"""
    try:
        tasks = await system_service.get_active_tasks()
        return {"tasks": tasks}
        
    except Exception as e:
        logger.error(f"Erro ao listar tarefas ativas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    current_user = Depends(get_admin_user)
):
    """Cancela uma tarefa em execução"""
    try:
        await system_service.cancel_task(task_id)
        return {"status": "task_cancelled"}
        
    except Exception as e:
        logger.error(f"Erro ao cancelar tarefa: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Endpoint de health check"""
    try:
        health = await system_service.check_health()
        return health
        
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        raise HTTPException(status_code=503, detail=str(e)) 