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

# 1. Configuração inicial do sistema
apt-get update && apt-get install -y \
    git python3-pip python3-venv redis-server net-tools ffmpeg \
    nvidia-cuda-toolkit nvidia-cuda-toolkit-gcc \
    pkg-config libicu-dev python3-dev wget curl

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
EOF

# Iniciar Redis em background
redis-server /etc/redis/redis.conf

# Verificar se Redis iniciou
echo "Aguardando Redis iniciar..."
for i in {1..30}; do
  if redis-cli ping > /dev/null 2>&1; then
    echo "Redis iniciado com sucesso!"
    break
  fi
  sleep 1
  if [ $i -eq 30 ]; then
    echo "Erro: Timeout aguardando Redis iniciar"
    exit 1
  fi
done

# 4. Configurar ambiente Python
python3 -m venv /workspace/venv_clean
source /workspace/venv_clean/bin/activate

# 5. Instalar dependências Python
pip install --upgrade pip wheel setuptools
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

scrape_configs:
  - job_name: 'media-api'
    static_configs:
      - targets: ['localhost:8000']
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

# Criar diretório de logs se não existir
mkdir -p /workspace/logs
touch /workspace/logs/{api,redis,prometheus,grafana}.log

nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers $(nproc) \
    --log-level info --log-file /workspace/logs/api.log &
API_PID=$!

# Verificar se API iniciou
echo "Aguardando API iniciar..."
for i in {1..30}; do
  if curl -s http://localhost:8000/health > /dev/null; then
    echo "API iniciada com sucesso!"
    break
  fi
  sleep 1
  if [ $i -eq 30 ]; then
    echo "Erro: Timeout aguardando API iniciar"
    exit 1
  fi
done

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