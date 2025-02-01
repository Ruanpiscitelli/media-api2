#!/bin/bash

echo "🧹 Limpando ambiente..."

# Parar todos os processos
pkill -f "uvicorn" || true
pkill -f "python main.py" || true
pkill -f "redis-server" || true
pkill -f "comfyui" || true

# Limpar caches
rm -rf /workspace/cache/*
redis-cli FLUSHALL || true

# Limpar logs
rm -f /workspace/logs/*.log

# Limpar ambiente Python
rm -rf /workspace/venv_clean
rm -rf /workspace/media-api2/__pycache__
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true

# Limpar arquivos temporários
rm -f /workspace/token.txt
rm -f /workspace/credentials.txt
rm -f /workspace/.env

# Limpar diretórios de mídia (opcional)
# rm -rf /workspace/media/{audio,images,video}/*

# Verificar processos restantes
echo -e "\nVerificando processos restantes:"
ps aux | grep -E "uvicorn|python|redis" | grep -v grep

echo "✅ Ambiente limpo!" 