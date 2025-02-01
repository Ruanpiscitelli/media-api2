#!/bin/bash
set -e

echo "Iniciando setup do Media API..."

# 1. Configuração inicial do sistema
apt-get update && apt-get install -y \
    git python3-pip python3-venv redis-server net-tools ffmpeg \
    nvidia-cuda-toolkit nvidia-cuda-toolkit-gcc \
    pkg-config libicu-dev python3-dev

# 2. Criar estrutura de diretórios
mkdir -p /workspace/{logs,media,cache,models,config,temp} \
        /workspace/models/{lora,checkpoints,vae} \
        /workspace/media/{audio,images,video}

# 3. Setup do ambiente Python
python3 -m venv /workspace/venv_clean
source /workspace/venv_clean/bin/activate

# 4. Instalar dependências
pip install --upgrade pip wheel setuptools
pip uninstall -y fastapi gradio uvicorn apscheduler  # Remover possíveis conflitos
pip install -r requirements/vast.txt
pip install -r requirements.txt

# 5. Configurar Redis
cat > /etc/redis/redis.conf << EOF
bind 127.0.0.1
port 6379
maxmemory 8gb
maxmemory-policy allkeys-lru
EOF

# 6. Iniciar serviços
service redis-server start

# 7. Configurar logs
mkdir -p /workspace/logs
touch /workspace/logs/{api,redis,gpu}.log

# 8. Iniciar API
cd /workspace/media-api2
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers $(nproc) \
    --log-level info --log-file /workspace/logs/api.log &

# 9. Monitoramento GPU
cat > /workspace/monitor.sh << 'EOF'
#!/bin/bash
while true; do
    nvidia-smi >> /workspace/logs/gpu.log
    sleep 60
done
EOF
chmod +x /workspace/monitor.sh
nohup /workspace/monitor.sh &

# Iniciar monitoramento GPU com config
python -m src.core.gpu.monitor --config /workspace/config/gpu_monitor.yaml &

echo "Setup concluído! Serviços iniciados:"
echo "- API: http://localhost:8000"
echo "- GUI: http://localhost:8080"
echo "- Redis: localhost:6379"

# Manter container rodando
tail -f /workspace/logs/*.log 