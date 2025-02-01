#!/bin/sh
# Usar /bin/sh em vez de /bin/bash para maior compatibilidade

# Log de debug
mkdir -p /workspace/logs
exec 1> >(tee -a /workspace/logs/startup.log) 2>&1
echo "Iniciando setup..."

# Configurar ambiente CUDA
export CUDA_HOME=/usr/local/cuda
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Criar diretórios
mkdir -p /workspace/ComfyUI/models/{checkpoints,clip,clip_vision,controlnet,ipadapter,loras,upscale_models,vae}

# Clonar repositórios
cd /workspace || exit 1
if [ ! -d "/workspace/media-api2" ]; then
    echo "Clonando media-api2..."
    git clone https://github.com/Ruanpiscitelli/media-api2.git
fi

if [ ! -d "/workspace/ComfyUI" ]; then
    echo "Clonando ComfyUI..."
    git clone https://github.com/comfyanonymous/ComfyUI.git
fi

# Instalar dependências
cd /workspace/media-api2 || exit 1
echo "Instalando dependências do media-api2..."
pip install -r requirements/vast.txt

# Configurar ComfyUI
cd /workspace/ComfyUI || exit 1
echo "Instalando dependências do ComfyUI..."
pip install -r requirements.txt

# Iniciar Redis
echo "Iniciando Redis..."
redis-server --daemonize yes

# Iniciar ComfyUI
echo "Iniciando ComfyUI..."
cd /workspace/ComfyUI || exit 1
python main.py --listen 0.0.0.0 --port 8188 --enable-cors-header > /workspace/logs/comfyui.log 2>&1 &

# Aguardar ComfyUI iniciar
sleep 5

# Iniciar API
echo "Iniciando API..."
cd /workspace/media-api2 || exit 1
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4 > /workspace/logs/api.log 2>&1 &

# Manter container rodando
echo "Setup completo. Monitorando logs..."
tail -f /workspace/logs/*.log