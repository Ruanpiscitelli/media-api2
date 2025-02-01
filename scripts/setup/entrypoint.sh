#!/bin/bash
set -e

echo "Iniciando setup do Media API..."

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
EOF

service redis-server restart

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
[security]
admin_user = admin
admin_password = admin
EOF

nohup ./bin/grafana-server --config=conf/custom.ini --homepath=. > /workspace/logs/grafana.log 2>&1 &

# 8. Iniciar API
cd /workspace/media-api2

# Criar diretório de logs se não existir
mkdir -p /workspace/logs
touch /workspace/logs/{api,redis,prometheus,grafana}.log

nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers $(nproc) \
    --log-level info --log-file /workspace/logs/api.log &

echo "Setup concluído! Serviços iniciados:"
echo "- API: http://localhost:8000"
echo "- Redis: localhost:6379"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3000"

# Manter container rodando e mostrar logs
tail -f /workspace/logs/*.log 