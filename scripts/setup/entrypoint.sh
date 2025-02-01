#!/bin/bash
set -e

echo "Iniciando setup do Media API..."

# Limpar arquivos temporários e downloads anteriores
cleanup() {
    echo "Limpando arquivos temporários..."
    rm -rf /workspace/*.tar.gz
    rm -rf /workspace/prometheus-*
    rm -rf /workspace/grafana-*
    rm -rf /workspace/*.deb
    rm -rf /workspace/dcgm-*
}

# Função para verificar requisitos do sistema (GPU etc.)
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

# Função para verificar ambiente virtual
check_venv() {
    echo "Verificando ambiente virtual..."
    if [ -d "/workspace/venv_clean" ]; then
        # Verificar se o ambiente virtual está funcionando
        source /workspace/venv_clean/bin/activate 2>/dev/null || return 1
        
        # Tentar usar python do venv
        if /workspace/venv_clean/bin/python3 -c "import sys; sys.exit(0)" 2>/dev/null; then
            echo "Ambiente virtual existente está OK"
            return 0
        fi
    fi
    return 1
}

# Função para verificar pip
check_pip() {
    if [ -f "/workspace/venv_clean/bin/pip" ]; then
        # Verificar se pip está funcionando
        if /workspace/venv_clean/bin/pip --version >/dev/null 2>&1; then
            echo "Pip já está instalado e funcionando"
            return 0
        fi
    fi
    return 1
}

# Limpar processos e arquivos antigos
cleanup
echo "Limpando processos anteriores..."
pkill -f uvicorn || true
redis-cli shutdown || true
sleep 2

# Verificar requisitos
check_requirements

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

# Iniciar Redis
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
done

# Configurar ambiente Python
if ! check_venv; then
    echo "Criando novo ambiente virtual..."
    rm -rf /workspace/venv_clean
    python3 -m venv --without-pip /workspace/venv_clean
fi

source /workspace/venv_clean/bin/activate

# Instalar/atualizar pip apenas se necessário
if ! check_pip; then
    echo "Instalando pip..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3
else
    echo "Atualizando pip..."
    python3 -m pip install --no-cache-dir -U pip
fi

# Verificar dependências instaladas
check_deps() {
    local pkg=$1
    if python3 -m pip freeze | grep -i "^$pkg==" >/dev/null; then
        return 0
    fi
    return 1
}

# Instalar dependências Python apenas se necessário
echo "Verificando dependências Python..."

# Sempre atualizar setuptools e wheel
python3 -m pip install --no-cache-dir -U setuptools wheel

# Verificar e instalar uvicorn
if ! check_deps "uvicorn"; then
    echo "Instalando uvicorn..."
    python3 -m pip install --no-cache-dir "uvicorn[standard]>=0.23.0"
fi

# Instalar dependências dos requirements apenas se necessário
if [ ! -f "/workspace/venv_clean/.requirements_installed" ]; then
    echo "Instalando dependências dos requirements..."
    python3 -m pip install --no-cache-dir -r requirements/vast.txt
    python3 -m pip install --no-cache-dir -r requirements.txt
    touch /workspace/venv_clean/.requirements_installed
else
    echo "Dependências dos requirements já instaladas"
fi

# Criar diretórios do projeto
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