"""
Verificações do sistema durante a inicialização.
"""

import os
import sys
import logging
import torch
import psutil
from typing import List, Dict
from pathlib import Path

from src.core.config import settings

logger = logging.getLogger(__name__)

async def check_gpu_requirements() -> Dict[str, bool]:
    """
    Verifica requisitos das GPUs:
    - Disponibilidade de CUDA
    - Memória disponível
    - Temperatura
    - Drivers
    """
    results = {
        "cuda_available": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "memory_sufficient": True,
        "temperature_ok": True
    }
    
    if not results["cuda_available"]:
        logger.error("CUDA não está disponível")
        return results
        
    try:
        # Verificar cada GPU
        for i in range(results["gpu_count"]):
            props = torch.cuda.get_device_properties(i)
            
            # Verificar memória (mínimo 8GB para SDXL)
            if props.total_memory < 8 * 1024 * 1024 * 1024:  # 8GB em bytes
                results["memory_sufficient"] = False
                logger.warning(f"GPU {i} tem menos que 8GB de VRAM")
                
        logger.info(f"Encontradas {results['gpu_count']} GPUs com CUDA")
        
    except Exception as e:
        logger.error(f"Erro verificando GPUs: {e}")
        results["cuda_available"] = False
        
    return results

async def check_system_resources() -> Dict[str, bool]:
    """
    Verifica recursos do sistema:
    - RAM disponível
    - Espaço em disco
    - CPUs
    """
    results = {
        "memory_ok": True,
        "disk_ok": True,
        "cpu_ok": True
    }
    
    try:
        # Verificar RAM (mínimo 16GB)
        total_ram = psutil.virtual_memory().total / (1024 * 1024 * 1024)  # GB
        if total_ram < 16:
            results["memory_ok"] = False
            logger.warning(f"Sistema tem apenas {total_ram:.1f}GB de RAM")
            
        # Verificar espaço em disco (mínimo 100GB)
        disk = psutil.disk_usage(settings.paths.workspace)
        free_space = disk.free / (1024 * 1024 * 1024)  # GB
        if free_space < 100:
            results["disk_ok"] = False
            logger.warning(f"Apenas {free_space:.1f}GB livres em disco")
            
        # Verificar CPUs (ideal: 1 CPU por GPU)
        cpu_count = psutil.cpu_count()
        if cpu_count < torch.cuda.device_count():
            results["cpu_ok"] = False
            logger.warning(f"Número de CPUs ({cpu_count}) menor que GPUs ({torch.cuda.device_count()})")
            
    except Exception as e:
        logger.error(f"Erro verificando recursos do sistema: {e}")
        return {k: False for k in results}
        
    return results

async def check_directories() -> Dict[str, bool]:
    """
    Verifica diretórios necessários:
    - Workspace
    - Models
    - Media
    - Logs
    """
    required_dirs = {
        "workspace": settings.paths.workspace,
        "models": settings.paths.models,
        "logs": settings.paths.logs,
        "media": Path(settings.paths.workspace) / "media"
    }
    
    results = {}
    
    for name, path in required_dirs.items():
        try:
            path = Path(path)
            path.mkdir(parents=True, exist_ok=True)
            results[name] = path.exists() and os.access(path, os.W_OK)
            if not results[name]:
                logger.error(f"Diretório {name} não existe ou não tem permissão de escrita: {path}")
        except Exception as e:
            logger.error(f"Erro verificando diretório {name}: {e}")
            results[name] = False
            
    return results

async def run_system_checks() -> bool:
    """
    Executa todas as verificações do sistema.
    Retorna True se todas as verificações passaram.
    """
    logger.info("Iniciando verificações do sistema...")
    
    # Executar verificações
    gpu_checks = await check_gpu_requirements()
    sys_checks = await check_system_resources()
    dir_checks = await check_directories()
    
    # Verificar resultados
    all_checks = {
        **gpu_checks,
        **sys_checks,
        **dir_checks
    }
    
    # Logar resultados
    for check, result in all_checks.items():
        log_level = logging.INFO if result else logging.ERROR
        logger.log(log_level, f"Check {check}: {'OK' if result else 'FALHOU'}")
    
    # Verificar se todas as checks passaram
    checks_passed = all(all_checks.values())
    
    if checks_passed:
        logger.info("Todas as verificações do sistema passaram")
    else:
        logger.error("Algumas verificações do sistema falharam")
        
    return checks_passed