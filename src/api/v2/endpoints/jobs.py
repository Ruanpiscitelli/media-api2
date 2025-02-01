"""
Endpoints para gerenciamento de jobs/tarefas.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime

from src.core.config import settings
from src.services.auth import get_current_user
from src.services.job_manager import JobManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])

# Schemas
class JobStatus(BaseModel):
    """Status de um job."""
    id: str = Field(..., description="ID do job")
    type: str = Field(..., description="Tipo do job")
    status: str = Field(..., description="Status atual")
    progress: float = Field(..., description="Progresso (0-100)")
    created_at: datetime = Field(..., description="Data de criação")
    started_at: Optional[datetime] = Field(None, description="Data de início")
    finished_at: Optional[datetime] = Field(None, description="Data de conclusão")
    error: Optional[str] = Field(None, description="Mensagem de erro se houver")
    result: Optional[dict] = Field(None, description="Resultado do job")
    metadata: dict = Field(default_factory=dict, description="Metadados adicionais")

class JobList(BaseModel):
    """Lista de jobs."""
    jobs: List[JobStatus] = Field(..., description="Lista de jobs")
    total: int = Field(..., description="Total de jobs")

# Endpoints
@router.get("", response_model=JobList)
async def list_jobs(
    type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    current_user = Depends(get_current_user)
):
    """
    Lista jobs/tarefas.
    Permite filtrar por tipo e status.
    """
    try:
        job_manager = JobManager()
        jobs = await job_manager.list_jobs(
            type=type,
            status=status,
            limit=limit,
            offset=offset,
            user_id=current_user.id
        )
        
        total = await job_manager.count_jobs(
            type=type,
            status=status,
            user_id=current_user.id
        )
        
        return {
            "jobs": jobs,
            "total": total
        }
        
    except Exception as e:
        logger.error(f"Erro listando jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{job_id}", response_model=JobStatus)
async def get_job(
    job_id: str,
    current_user = Depends(get_current_user)
):
    """
    Obtém status detalhado de um job específico.
    """
    try:
        job_manager = JobManager()
        job = await job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job não encontrado")
            
        # Verificar permissão
        if job.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Acesso negado")
            
        return job
        
    except Exception as e:
        logger.error(f"Erro obtendo job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user = Depends(get_current_user)
):
    """
    Cancela um job em execução.
    """
    try:
        job_manager = JobManager()
        job = await job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job não encontrado")
            
        # Verificar permissão
        if job.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Acesso negado")
            
        # Cancelar job
        await job_manager.cancel_job(job_id)
        
        return {
            "status": "success",
            "message": "Job cancelado com sucesso"
        }
        
    except Exception as e:
        logger.error(f"Erro cancelando job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    current_user = Depends(get_current_user)
):
    """
    Remove um job e seus recursos associados.
    """
    try:
        job_manager = JobManager()
        job = await job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job não encontrado")
            
        # Verificar permissão
        if job.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Acesso negado")
            
        # Remover job
        await job_manager.delete_job(job_id)
        
        return {
            "status": "success",
            "message": "Job removido com sucesso"
        }
        
    except Exception as e:
        logger.error(f"Erro removendo job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    level: Optional[str] = None,
    limit: int = 100,
    current_user = Depends(get_current_user)
):
    """
    Obtém logs de um job específico.
    """
    try:
        job_manager = JobManager()
        job = await job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job não encontrado")
            
        # Verificar permissão
        if job.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Acesso negado")
            
        # Obter logs
        logs = await job_manager.get_job_logs(
            job_id=job_id,
            start_time=start_time,
            end_time=end_time,
            level=level,
            limit=limit
        )
        
        return {
            "logs": logs,
            "total": len(logs)
        }
        
    except Exception as e:
        logger.error(f"Erro obtendo logs do job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 