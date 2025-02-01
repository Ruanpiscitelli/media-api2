#!/bin/bash
set -e

echo "Iniciando setup do Media API..."

# Função para verificar requisitos
check_requirements() {
    echo "Verificando requisitos do sistema..."
    
    # Verificar GPUs
    gpu_count=$(nvidia-smi --query-gpu=gpu_name --format=csv,noheader | wc -l)
    echo "GPUs encontradas: $gpu_count"
    if [ "$gpu_count" -eq 0 ]; then
        echo "Erro: Nenhuma GPU encontrada"
        exit 1
    fi
    
    # Mostrar informações das GPUs
    echo "Informações das GPUs:"
    nvidia-smi --query-gpu=gpu_name,memory.total,driver_version --format=csv
}

# Limpar processos antigos
echo "Limpando processos anteriores..."
pkill -f uvicorn || true
redis-cli shutdown || true
sleep 2

# Verificar requisitos
check_requirements

# Instalar dependências básicas
apt-get update && apt-get install -y \
    redis-server python3-pip python3-venv \
    nvidia-cuda-toolkit ffmpeg

# Configurar Redis básico
mkdir -p /var/log/redis
cat > /etc/redis/redis.conf << EOF
bind 127.0.0.1
port 6379
maxmemory 8gb
maxmemory-policy allkeys-lru
daemonize yes
pidfile /var/run/redis/redis-server.pid
logfile /var/log/redis/redis-server.log
dir /var/lib/redis
EOF

# Criar diretórios necessários para o Redis
mkdir -p /var/run/redis /var/lib/redis
chown -R redis:redis /var/run/redis /var/lib/redis /var/log/redis

# Iniciar Redis (sem systemd)
echo "Iniciando Redis..."
redis-server /etc/redis/redis.conf

# Aguardar Redis iniciar
echo "Aguardando Redis iniciar..."
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if redis-cli ping | grep -q "PONG"; then
        echo "Redis iniciado com sucesso!"
        break
    fi
    echo "Tentativa $attempt de $max_attempts..."
    sleep 1
    attempt=$((attempt+1))
    
    if [ $attempt -eq $max_attempts ]; then
        echo "Erro: Redis não iniciou. Verificando logs:"
        tail -n 50 /var/log/redis/redis-server.log
        exit 1
    fi
done

# Verificar Redis
echo "Verificando Redis..."
redis-cli ping

# Remover ambiente virtual antigo se existir
rm -rf /workspace/venv_clean

# Configurar ambiente Python
echo "Criando novo ambiente virtual..."
python3 -m venv --without-pip /workspace/venv_clean
source /workspace/venv_clean/bin/activate

# Instalar pip manualmente no ambiente virtual
curl -sS https://bootstrap.pypa.io/get-pip.py | python3

# Verificar instalação
which python3
which pip

# Instalar dependências Python
echo "Instalando dependências Python..."
python3 -m pip install --no-cache-dir -U pip setuptools wheel
python3 -m pip install --no-cache-dir "uvicorn[standard]>=0.23.0"
python3 -m pip install --no-cache-dir -r requirements/vast.txt
python3 -m pip install --no-cache-dir -r requirements.txt

# Criar diretórios necessários
mkdir -p /workspace/{logs,media,models} \
        /workspace/media/{audio,images,video}

# Configurar variáveis de ambiente
export PYTHONPATH=/workspace/media-api2
export CUDA_VISIBLE_DEVICES=0,1,2,3

# Iniciar API
echo "Iniciando API..."
python -m uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    > /workspace/logs/api.log 2>&1 &

# Verificar se API iniciou
echo "Verificando API..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        echo "API iniciada com sucesso!"
        break
    fi
    sleep 1
done

# Script simples de monitoramento
while true; do
    echo "=== Status do Sistema ==="
    echo "GPU Status:"
    nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu --format=csv
    echo "Processos:"
    ps aux | grep -E "uvicorn|redis"
    sleep 60
done &

echo "Setup concluído!"
echo "API: http://localhost:8000"
echo "Redis: localhost:6379"

# Manter logs visíveis
tail -f /workspace/logs/api.log 