#!/bin/bash

echo "🧹 Limpando ambiente..."

# Parar todos os processos
pkill -f "uvicorn"
pkill -f "python main.py"
pkill -f "redis-server"

# Limpar caches
rm -rf /workspace/cache/*
redis-cli FLUSHALL

# Limpar logs
rm -f /workspace/logs/*.log

# Limpar ambiente Python
rm -rf /workspace/venv_clean
rm -rf /workspace/media-api2/__pycache__
find . -type d -name "__pycache__" -exec rm -r {} +

echo "✅ Ambiente limpo!" 