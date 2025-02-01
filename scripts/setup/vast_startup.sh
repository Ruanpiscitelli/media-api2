#!/bin/bash
set -e  # Para o script se houver algum erro

# Log de debug
exec 1> >(tee -a /workspace/logs/startup.log) 2>&1
echo "Iniciando setup..."

# Configurar ambiente CUDA
export CUDA_HOME=/usr/local/cuda
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Criar diretórios
mkdir -p /workspace/logs
mkdir -p /workspace/ComfyUI/models/{checkpoints,clip,clip_vision,controlnet,ipadapter,loras,upscale_models,vae}

# Verificar se os repositórios já existem
if [ ! -d "/workspace/media-api2" ]; then
    echo "Clonando media-api2..."
    git clone https://github.com/Ruanpiscitelli/media-api2.git
fi

if [ ! -d "/workspace/ComfyUI" ]; then
    echo "Clonando ComfyUI..."
    git clone https://github.com/comfyanonymous/ComfyUI.git
fi

# Instalar dependências
cd /workspace/media-api2
echo "Instalando dependências do media-api2..."
pip install -r requirements/vast.txt

# Configurar ComfyUI
cd /workspace/ComfyUI
echo "Instalando dependências do ComfyUI..."
pip install -r requirements.txt

# Iniciar Redis
echo "Iniciando Redis..."
service redis-server start || {
    echo "Erro ao iniciar Redis. Tentando recuperar..."
    rm -f /var/run/redis/redis-server.pid
    service redis-server start
}

# Iniciar ComfyUI
echo "Iniciando ComfyUI..."
cd /workspace/ComfyUI
nohup python main.py --listen 0.0.0.0 --port 8188 --enable-cors-header > /workspace/logs/comfyui.log 2>&1 &

# Aguardar ComfyUI iniciar
sleep 10

# Iniciar API
echo "Iniciando API..."
cd /workspace/media-api2
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4 > /workspace/logs/api.log 2>&1 &

# Verificar se os serviços estão rodando
echo "Verificando serviços..."
sleep 5

check_service() {
    if pgrep -f "$1" > /dev/null; then
        echo "$1 está rodando"
        return 0
    else
        echo "$1 não está rodando"
        return 1
    fi
}

check_service "redis-server"
check_service "main.py"
check_service "uvicorn"

# Manter container rodando e mostrar logs
echo "Setup completo. Monitorando logs..."
exec tail -f /workspace/logs/*.log