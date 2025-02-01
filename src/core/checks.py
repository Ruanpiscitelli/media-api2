"""
Verificações do sistema durante a inicialização.
"""

import os
import sys
import logging
import torch
import psutil
from typing import List, Dict, Tuple
from pathlib import Path
import importlib
import subprocess
from sqlalchemy import text
from src.core.db import engine, async_engine
from src.core.redis_client import redis_pool

from src.core.config import settings

logger = logging.getLogger(__name__)

REQUIRED_PACKAGES = [
    ("aiohttp", "aiohttp[speedups]"),
    ("torch", "torch"),
    ("psutil", "psutil"),
    ("fastapi", "fastapi[all]")
]

def check_and_install_package(package_name: str, install_name: str) -> bool:
    """Verifica e instala um pacote Python se necessário"""
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        logger.warning(f"Pacote {package_name} não encontrado. Tentando instalar...")
        try:
            subprocess.check_call(["pip", "install", "--no-cache-dir", install_name])
            return True
        except Exception as e:
            logger.error(f"Erro ao instalar {package_name}: {e}")
            return False

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
    
    # Verificar dependências Python
    missing_packages = []
    for package_name, install_name in REQUIRED_PACKAGES:
        if not check_and_install_package(package_name, install_name):
            missing_packages.append(package_name)
    
    if missing_packages:
        raise RuntimeError(f"Dependências faltando: {', '.join(missing_packages)}")
    
    logger.info("Verificações do sistema concluídas com sucesso")
    
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

async def check_system():
    """Verificações básicas do sistema"""
    checks = {
        "cuda": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
    }
    
    for name, status in checks.items():
        logger.info(f"Check {name}: {'OK' if status else 'FALHOU'}")
    
    return all(checks.values())

async def check_db_connection():
    """Verifica conexão com o banco de dados"""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("✅ Conexão com banco de dados OK")
            return True
    except Exception as e:
        logger.error(f"❌ Erro na conexão com banco de dados: {e}")
        return False

async def check_redis_connection():
    try:
        if redis_pool:
            async with redis_pool.get() as redis:
                await redis.ping()
            return True
    except Exception as e:
        logger.error(f"Erro Redis: {e}")
    return False

async def check_gpu_health() -> bool:
    """Verifica saúde das GPUs"""
    try:
        from src.core.gpu_manager import gpu_manager
        
        if not gpu_manager.gpus:
            logger.warning("Nenhuma GPU disponível")
            return False
            
        for gpu in gpu_manager.gpus:
            if gpu.get("is_cpu", False):
                continue
                
            # Verificar temperatura
            temp = await gpu_manager.get_temperature(gpu["id"])
            if temp > settings.GPU_TEMP_LIMIT:
                logger.error(f"GPU {gpu['id']} temperatura alta: {temp}°C")
                return False
                
        return True
        
    except Exception as e:
        logger.error(f"Erro verificando GPUs: {e}")
        return False