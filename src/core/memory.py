"""
Gerenciamento de memória e limpeza
"""
import gc
import psutil
import torch
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)

def clear_gpu_memory():
    """Limpa memória GPU"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()

def clear_system_memory():
    """Limpa memória do sistema"""
    gc.collect()
    
    # Força Python a liberar memória para o SO
    import ctypes
    libc = ctypes.CDLL('libc.so.6')
    libc.malloc_trim(0)

def check_memory_usage():
    """Verifica uso de memória"""
    memory = psutil.virtual_memory()
    if memory.percent > settings.MEMORY_THRESHOLD:
        logger.warning(f"Uso de memória alto: {memory.percent}%")
        clear_system_memory()
        clear_gpu_memory() 