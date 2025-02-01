#!/bin/bash

echo "Verificando ambiente..."

# Verificar Python e virtualenv
which python
python --version
which pip
pip list

# Verificar Redis
redis-cli ping

# Verificar diretórios
ls -la /workspace/temp
ls -la /workspace/outputs/suno
ls -la /workspace/cache/suno
ls -la /workspace/logs

# Verificar configurações
cat /workspace/media-api2/.env

# Verificar logs
tail -n 50 /workspace/logs/api.log

# Verificar processos
ps aux | grep python
ps aux | grep redis