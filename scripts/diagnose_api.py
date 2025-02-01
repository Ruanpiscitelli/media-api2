"""
Script para executar diagnóstico da API
"""
import asyncio
import sys
from src.core.diagnostics import run_diagnostics

if __name__ == "__main__":
    success = asyncio.run(run_diagnostics())
    sys.exit(0 if success else 1) 