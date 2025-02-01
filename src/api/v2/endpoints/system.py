"""
Endpoints para monitoramento e gerenciamento do sistema.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from src.core.auth import get_current_user, get_admin_user
from src.services.system import SystemService
from src.services.monitoring import MonitoringService
from src.services.queue import QueueService
import logging
from datetime import datetime
import psutil
import time
import asyncio

router = APIRouter(prefix="/system", tags=["Sistema"])
logger = logging.getLogger(__name__)

system_service = SystemService()
monitoring_service = MonitoringService()
queue_service = QueueService()

class SystemStatus(BaseModel):
    """
    Modelo para status do sistema.
    
    Attributes:
        status: Estado atual do sistema (online/offline)
        gpu_usage: Uso de cada GPU em porcentagem
        queue_size: Número total de tarefas na fila
        active_workers: Número de workers ativos
        uptime: Tempo de atividade em segundos
    """
    status: str = Field(..., description="Estado atual do sistema")
    gpu_usage: Dict[str, float] = Field(..., description="Uso de cada GPU em %")
    queue_size: int = Field(..., description="Total de tarefas na fila")
    active_workers: int = Field(..., description="Número de workers ativos")
    uptime: float = Field(..., description="Tempo de atividade em segundos")

class QueueStatus(BaseModel):
    """Modelo para status das filas"""
    high_priority: int
    normal: int
    batch: int
    total_tasks: int

class LogEntry(BaseModel):
    """
    Modelo para entrada de log.
    
    Attributes:
        timestamp: Data/hora do log
        level: Nível do log (INFO, ERROR, etc)
        message: Mensagem do log
    """
    timestamp: datetime = Field(..., description="Data/hora do log")
    level: str = Field(..., description="Nível do log")
    message: str = Field(..., description="Mensagem do log")

class ProcessInfo(BaseModel):
    """Informações de um processo"""
    pid: int
    name: str
    command: str
    status: str
    cpu_percent: float
    memory_percent: float
    gpu_id: Optional[int]
    gpu_memory_used: Optional[int]
    uptime: float

@router.get(
    "/status",
    response_model=SystemStatus,
    summary="Status do Sistema",
    description="""
    Retorna o status atual do sistema incluindo:
    - Estado geral do sistema
    - Uso de cada GPU
    - Tamanho da fila de processamento
    - Número de workers ativos
    - Tempo de atividade
    """,
    responses={
        200: {
            "description": "Status obtido com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "status": "online",
                        "gpu_usage": {"gpu0": 45.5, "gpu1": 32.1},
                        "queue_size": 5,
                        "active_workers": 2,
                        "uptime": 86400.5
                    }
                }
            }
        },
        500: {
            "description": "Erro ao obter status do sistema",
            "content": {
                "application/json": {
                    "example": {"detail": "Erro ao conectar com serviço de monitoramento"}
                }
            }
        }
    }
)
async def get_system_status():
    """Retorna o status atual do sistema."""
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

@router.get(
    "/logs",
    response_model=List[LogEntry],
    summary="Logs do Sistema",
    description="""
    Retorna logs do sistema com opções de filtro:
    - Por serviço (api, comfyui, system)
    - Por quantidade de linhas
    - Por nível de log
    """,
    responses={
        200: {
            "description": "Logs obtidos com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "logs": [
                            {
                                "timestamp": "2024-01-30T12:00:00Z",
                                "level": "INFO",
                                "message": "Sistema iniciado com sucesso"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def get_system_logs(
    service: str = Query(
        "all",
        description="Serviço para filtrar logs (all, api, comfyui, system)"
    ),
    limit: int = Query(
        100,
        description="Número máximo de linhas",
        gt=0,
        le=1000
    ),
    level: Optional[str] = Query(
        None,
        description="Filtrar por nível de log (INFO, ERROR, etc)"
    )
):
    """Retorna logs do sistema com opções de filtro."""
    try:
        logs = await monitoring_service.get_logs(
            level=level,
            service=service,
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

@router.get("/processes", response_model=List[ProcessInfo])
async def list_processes(
    current_user = Depends(get_admin_user)
):
    """Lista todos os processos do sistema"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status', 'cpu_percent', 'memory_percent', 'create_time']):
            try:
                info = proc.info
                # Obtém informações de GPU se disponível
                gpu_info = await gpu_manager.get_process_gpu_info(info['pid'])
                
                processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "command": ' '.join(info['cmdline'] or []),
                    "status": info['status'],
                    "cpu_percent": info['cpu_percent'] or 0.0,
                    "memory_percent": info['memory_percent'] or 0.0,
                    "gpu_id": gpu_info['gpu_id'] if gpu_info else None,
                    "gpu_memory_used": gpu_info['memory_used'] if gpu_info else None,
                    "uptime": time.time() - info['create_time']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return {"processes": processes}
        
    except Exception as e:
        logger.error(f"Erro listando processos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/processes/{pid}/kill")
async def kill_process(
    pid: int,
    current_user = Depends(get_admin_user)
):
    """Mata um processo específico"""
    try:
        process = psutil.Process(pid)
        process.kill()
        return {"status": "success", "message": f"Process {pid} killed"}
    except psutil.NoSuchProcess:
        raise HTTPException(status_code=404, detail=f"Process {pid} not found")
    except Exception as e:
        logger.error(f"Erro matando processo {pid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/processes/{pid}/restart")
async def restart_process(
    pid: int,
    current_user = Depends(get_admin_user)
):
    """Reinicia um processo específico"""
    try:
        process = psutil.Process(pid)
        cmd = process.cmdline()
        process.kill()
        
        # Aguarda o processo terminar
        process.wait(timeout=5)
        
        # Reinicia o processo
        new_process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        return {
            "status": "success",
            "message": f"Process {pid} restarted",
            "new_pid": new_process.pid
        }
        
    except psutil.NoSuchProcess:
        raise HTTPException(status_code=404, detail=f"Process {pid} not found")
    except Exception as e:
        logger.error(f"Erro reiniciando processo {pid}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 