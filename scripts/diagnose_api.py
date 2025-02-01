"""
Script para executar diagnóstico da API
"""
import os
import sys
import asyncio
from pathlib import Path

# Adicionar diretório raiz do projeto ao PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.core.diagnostics import run_diagnostics

if __name__ == "__main__":
    success = asyncio.run(run_diagnostics())
    sys.exit(0 if success else 1) 