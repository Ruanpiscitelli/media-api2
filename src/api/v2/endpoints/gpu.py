from fastapi import APIRouter, Depends, HTTPException
from src.core.gpu.manager import GPUManager
from src.core.queue.priority_manager import PriorityQueue
from src.security.user import User
from src.utils.exceptions import GPUBusyError

app = APIRouter()

@app.post("/gpu/allocate")
async def allocate_gpu(
    request: GpuAllocationRequest,
    user: User = Depends(get_admin_user)
):
    """Aloca GPUs específicas para tarefas críticas"""
    try:
        allocation = await gpu_manager.reserve_gpus(
            request.gpu_ids,
            request.task_type
        )
        return {"status": "allocated", "gpus": allocation}
    except GPUBusyError as e:
        raise HTTPException(409, detail=str(e)) 