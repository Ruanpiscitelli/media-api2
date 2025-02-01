#!/bin/bash
set -e

echo "Iniciando setup do Media API..."

# Função para verificar se porta está em uso
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo "Porta $port já está em uso. Tentando limpar..."
        # Tenta matar o processo usando a porta
        lsof -ti :$port | xargs kill -9 2>/dev/null
        sleep 2
    fi
}

# Função para limpar processos anteriores
cleanup_old_processes() {
    echo "Limpando processos anteriores..."
    pkill -f prometheus || true
    pkill -f grafana-server || true
    pkill -f uvicorn || true
    redis-cli shutdown || true
    sleep 2
}

# Limpar processos antigos e verificar portas
cleanup_old_processes
check_port 3000  # Grafana
check_port 9090  # Prometheus
check_port 8000  # API
check_port 6379  # Redis

# Função para verificar requisitos
check_requirements() {
    echo "Verificando requisitos do sistema..."
    
    # Verificar versão do Python
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    echo "Versão do Python: $python_version"
    if [[ $(echo "$python_version" | cut -d. -f1,2) < "3.10" ]]; then
        echo "Erro: Python 3.10 ou superior é necessário"
        exit 1
    fi
    
    # Verificar CUDA
    if ! command -v nvcc &> /dev/null; then
        echo "Erro: CUDA não encontrado"
        exit 1
    fi
    echo "CUDA encontrado: $(nvcc --version | head -n1)"
    
    # Verificar GPUs disponíveis
    gpu_count=$(nvidia-smi --query-gpu=gpu_name --format=csv,noheader | wc -l)
    echo "GPUs encontradas: $gpu_count"
    if [ "$gpu_count" -eq 0 ]; then
        echo "Erro: Nenhuma GPU encontrada"
        exit 1
    fi
}

# Adicionar antes da instalação das dependências
check_requirements

# 1. Configuração inicial do sistema
apt-get update && apt-get install -y \
    git python3-pip python3-venv redis-server net-tools ffmpeg \
    nvidia-cuda-toolkit nvidia-cuda-toolkit-gcc \
    pkg-config libicu-dev python3-dev wget curl \
    prometheus-node-exporter \
    prometheus-redis-exporter \
    nvidia-dcgm-exporter

# 2. Criar estrutura de diretórios
mkdir -p /workspace/{logs,media,cache,models,config,temp} \
        /workspace/models/{lora,checkpoints,vae} \
        /workspace/media/{audio,images,video}

# 3. Configurar Redis
cat > /etc/redis/redis.conf << EOF
bind 127.0.0.1
port 6379
maxmemory 8gb
maxmemory-policy allkeys-lru
daemonize yes
supervised systemd
dir /var/lib/redis
pidfile /var/run/redis/redis-server.pid

# Configurações de métricas
latency-tracking yes
latency-monitoring-threshold 25
slowlog-log-slower-than 10000
slowlog-max-len 128

# Configurações de performance
maxclients 10000
timeout 0
tcp-keepalive 300
databases 16

# Configurações de persistência
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes

# Configurações de logging
loglevel notice
logfile /var/log/redis/redis-server.log
syslog-enabled yes
syslog-ident redis
syslog-facility local0
EOF

# Garantir que diretórios existam e permissões estejam corretas
mkdir -p /var/lib/redis /var/run/redis
chown -R redis:redis /var/lib/redis /var/run/redis /etc/redis
chmod 750 /var/lib/redis /var/run/redis

# Parar qualquer instância existente do Redis
service redis-server stop || true
killall -9 redis-server || true

# Iniciar Redis como serviço
service redis-server start

# Verificar se Redis iniciou
echo "Aguardando Redis iniciar..."
for i in {1..30}; do
  echo "Tentativa $i de 30..."
  if redis-cli ping > /dev/null 2>&1; then
    echo "Redis iniciado com sucesso!"
    break
  fi
  # Se Redis não iniciou, tentar iniciar novamente
  if [ $i -eq 15 ]; then
    echo "Tentando reiniciar Redis..."
    service redis-server restart
  fi
  sleep 1
  if [ $i -eq 30 ]; then
    echo "Erro: Timeout aguardando Redis iniciar. Verificando status:"
    service redis-server status
    echo "Logs do Redis:"
    tail -n 20 /var/log/redis/redis-server.log
    exit 1
  fi
done

# 4. Configurar ambiente Python
python3 -m venv /workspace/venv_clean --clear  # --clear para garantir ambiente limpo
source /workspace/venv_clean/bin/activate

# 5. Instalar dependências Python
python -m pip install --no-cache-dir -U pip setuptools wheel

# Instalar uvicorn primeiro
pip install "uvicorn[standard]>=0.23.0"

# Instalar PyTorch com CUDA 11.8
pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Instalar outras dependências
pip install -r requirements/vast.txt
pip install -r requirements.txt

# 6. Configurar e iniciar Prometheus
cd /workspace
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*/

# Configuração básica do Prometheus
cat > prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'media-api'
    static_configs:
      - targets: ['localhost:8000']
    
  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
    
  - job_name: 'nvidia-gpu'
    static_configs:
      - targets: ['localhost:9835']

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
EOF

nohup ./prometheus --config.file=prometheus.yml --web.listen-address=:9090 > /workspace/logs/prometheus.log 2>&1 &
PROMETHEUS_PID=$!

# Verificar se Prometheus iniciou
echo "Aguardando Prometheus iniciar..."
for i in {1..30}; do
  if curl -s http://localhost:9090/-/healthy > /dev/null; then
    echo "Prometheus iniciado com sucesso!"
    break
  fi
  sleep 1
  if [ $i -eq 30 ]; then
    echo "Erro: Timeout aguardando Prometheus iniciar"
    exit 1
  fi
done

# 7. Configurar e iniciar Grafana
cd /workspace
wget https://dl.grafana.com/oss/release/grafana-10.0.3.linux-amd64.tar.gz
tar -zxvf grafana-*.tar.gz
cd grafana-*/

# Configuração básica do Grafana
mkdir -p conf
cat > conf/custom.ini << EOF
[server]
http_port = 3000
domain = localhost
protocol = http
root_url = %(protocol)s://%(domain)s:%(http_port)s/
[security]
admin_user = admin
admin_password = admin
[paths]
data = /workspace/grafana/data
logs = /workspace/grafana/logs
plugins = /workspace/grafana/plugins
EOF

# Criar diretórios necessários para Grafana
mkdir -p /workspace/grafana/{data,logs,plugins}

nohup ./bin/grafana-server --config=conf/custom.ini --homepath=. > /workspace/logs/grafana.log 2>&1 &
GRAFANA_PID=$!

# Verificar se Grafana iniciou
echo "Aguardando Grafana iniciar..."
for i in {1..30}; do
  if curl -s http://localhost:3000/api/health > /dev/null; then
    echo "Grafana iniciado com sucesso!"
    break
  fi
  sleep 1
  if [ $i -eq 30 ]; then
    echo "Erro: Timeout aguardando Grafana iniciar"
    exit 1
  fi
done

# 8. Iniciar API
cd /workspace/media-api2

# Criar arquivo .env se não existir
if [ ! -f .env ]; then
    echo "Criando arquivo .env..."
    cat > .env << EOF
# Ambiente
ENV=production
DEBUG=false
ENVIRONMENT=production

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_SSL=false
REDIS_TIMEOUT=5
REDIS_MAX_CONNECTIONS=10

# Rate Limiting
RATE_LIMIT_DEFAULT=100
RATE_LIMIT_BURST=10
RATE_LIMIT_STRATEGY=fixed-window

# Servidor
HOST=0.0.0.0
PORT=8000
WORKERS=4
REQUEST_TIMEOUT=300

# Segurança
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
BACKEND_CORS_ORIGINS='["*"]'

# Logging
LOG_LEVEL=info
JSON_LOGS=true

# API
PROJECT_NAME="Media API"
VERSION="2.0.0"
API_V2_STR="/api/v2"

# Database
DATABASE_URL="sqlite:///./sql_app.db"

# Cache
CACHE_TTL=3600
CACHE_MAX_SIZE=10000

# GPU
GPU_DEVICES=0,1,2,3
GPU_TEMP_LIMIT=85
GPU_UTIL_THRESHOLD=95
GPU_MEMORY_HEADROOM=1024

# Monitoramento
ENABLE_PROMETHEUS=true
PROMETHEUS_PORT=9090
ENABLE_GRAFANA=true
GRAFANA_PORT=3000

# Recursos
MEMORY_THRESHOLD_MB=8192
TEMP_FILE_MAX_AGE=3600

# ComfyUI
COMFY_API_URL="http://localhost:8188/api"
COMFY_WS_URL="ws://localhost:8188/ws"
COMFY_TIMEOUT=30
MAX_CONCURRENT_RENDERS=4
MAX_RENDER_TIME=300
MAX_VIDEO_LENGTH=300
MAX_VIDEO_SIZE=100000000
RENDER_TIMEOUT_SECONDS=300
EOF
fi

# Verificar se o ambiente virtual está ativado
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Ativando ambiente virtual..."
    source /workspace/venv_clean/bin/activate
fi

# Verificar instalação do uvicorn
python -m pip install "uvicorn[standard]>=0.23.0" || {
    echo "Uvicorn não encontrado. Instalando..."
    pip install "uvicorn[standard]>=0.23.0"
}

# Verificar se as dependências estão instaladas
echo "Verificando dependências da API..."
echo "Listando pacotes instalados:"
pip list | grep -E "uvicorn|fastapi"

echo "Verificando conteúdo do ambiente virtual:"
ls -la $VIRTUAL_ENV/bin/

pip install -r requirements/vast.txt
pip install -r requirements.txt

# Configurar variáveis de ambiente necessárias
export PYTHONPATH=/workspace/media-api2
export CUDA_VISIBLE_DEVICES=0
export PATH=$VIRTUAL_ENV/bin:$PATH

echo "Iniciando API..."
echo "PYTHONPATH: $PYTHONPATH"
echo "Python executável: $(which python)"
echo "Diretório atual: $(pwd)"
echo "Conteúdo do diretório src:"
ls -la src/

echo "Iniciando API com configurações otimizadas..."
if python -m uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers $((2 * $(nproc))) \  # 2 workers por CPU
    --loop uvloop \
    --http httptools \
    --log-level info \
    --proxy-headers \
    --forwarded-allow-ips='*' \
    --timeout-keep-alive 75 \
    --backlog 2048 \
    --limit-concurrency 1000 \
    --no-access-log \
    > /workspace/logs/api.log 2>&1 &
then
    API_PID=$!
    echo "API iniciada com sucesso (PID: $API_PID)"
else
    echo "Erro ao iniciar API. Verificando logs:"
    tail -n 50 /workspace/logs/api.log
    exit 1
fi

# Melhorar verificação de saúde da API
echo "Verificando saúde da API..."
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    echo "Tentativa $attempt de $max_attempts..."
    if curl -s http://localhost:8000/health | grep -q '"status":"healthy"'; then
        echo "API está saudável!"
        break
    elif [ $attempt -eq $((max_attempts/2)) ]; then
        echo "Logs da API até agora:"
        tail -n 100 /workspace/logs/api.log
    fi
    attempt=$((attempt+1))
    sleep 2
done

if [ $attempt -gt $max_attempts ]; then
    echo "Erro: API não iniciou corretamente. Logs finais:"
    tail -n 200 /workspace/logs/api.log
    exit 1
fi

# Adicionar monitoramento de recursos
while true; do
    # Monitorar uso de CPU
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
    echo "Uso de CPU: $cpu_usage%"
    
    # Monitorar memória
    free -h
    
    # Monitorar GPUs
    nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu --format=csv,noheader
    
    # Verificar processos
    ps aux | grep -E "uvicorn|redis|prometheus|grafana"
    
    sleep 60
done &
MONITOR_PID=$!

# Registrar PID do monitoramento
echo $MONITOR_PID > /workspace/monitor.pid

echo "Setup concluído! Serviços iniciados:"
echo "- API: http://localhost:8000"
echo "- Redis: localhost:6379"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3000"

# Função para parar serviços graciosamente
cleanup() {
    echo "Parando serviços..."
    echo "Parando Prometheus..."
    kill $PROMETHEUS_PID 2>/dev/null
    wait $PROMETHEUS_PID 2>/dev/null

    echo "Parando Grafana..."
    kill $GRAFANA_PID 2>/dev/null
    wait $GRAFANA_PID 2>/dev/null

    echo "Parando API..."
    kill $API_PID 2>/dev/null
    wait $API_PID 2>/dev/null

    echo "Parando Redis..."
    redis-cli shutdown

    echo "Todos os serviços parados."
    exit 0
}

# Registrar função de cleanup para SIGTERM e SIGINT
trap cleanup SIGTERM SIGINT
trap cleanup EXIT

# Manter container rodando e mostrar logs
tail -f /workspace/logs/*.log 