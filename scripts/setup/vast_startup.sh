#!/bin/bash

# Configurar log detalhado
exec 1> >(tee -a "/workspace/logs/setup.log") 2>&1
echo "[$(date)] Iniciando setup..."

# Função para verificar erros
check_error() {
    if [ $? -ne 0 ]; then
        echo "[ERRO] $1"
        exit 1
    fi
}

# Criar diretórios necessários
echo "Criando diretórios..."
mkdir -p /workspace/{logs,media,cache,models,media/temp,models/lora,models/checkpoints}
check_error "Falha ao criar diretórios"

# Instalar dependências adicionais
echo "Instalando dependências adicionais..."
apt-get update && apt-get install -y \
    redis-server \
    net-tools \
    ffmpeg \
    git-lfs
check_error "Falha ao instalar dependências"

# Iniciar Redis
echo "Iniciando Redis..."
service redis-server start
check_error "Falha ao iniciar Redis"

# Usar o ambiente Python existente
echo "Configurando ambiente Python..."
source /opt/conda/bin/activate
check_error "Falha ao ativar ambiente conda"

# Clonar repositórios
echo "Clonando repositórios..."
if [ ! -d "/workspace/media-api2" ]; then
    git clone https://github.com/Ruanpiscitelli/media-api2.git /workspace/media-api2
    check_error "Falha ao clonar media-api2"
fi

# Configurar ComfyUI
echo "Configurando ComfyUI..."
if [ ! -d "/workspace/ComfyUI" ]; then
    git clone https://github.com/comfyanonymous/ComfyUI.git /workspace/ComfyUI
    check_error "Falha ao clonar ComfyUI"

    # Instalar custom nodes
    cd /workspace/ComfyUI/custom_nodes
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git
    git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git
    git clone https://github.com/pythongosssss/ComfyUI-Custom-Scripts.git
    git clone https://github.com/ltdrdata/ComfyUI-Impact-Pack.git
    git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
    
    # Criar diretório de modelos do ComfyUI
    mkdir -p /workspace/ComfyUI/models/{checkpoints,clip,clip_vision,controlnet,ipadapter,loras,upscale_models,vae}
    
    # Download dos modelos base (SDXL base e VAE)
    cd /workspace/ComfyUI/models/checkpoints
    wget -O sd_xl_base_1.0.safetensors https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
    wget -O sd_xl_refiner_1.0.safetensors https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors
    
    cd /workspace/ComfyUI/models/vae
    wget -O sdxl_vae.safetensors https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors
fi

# Instalar dependências Python adicionais
echo "Instalando dependências Python adicionais..."
cd /workspace/media-api2
pip install -r requirements/vast.txt
check_error "Falha ao instalar dependências Python"

# Instalar dependências do ComfyUI
cd /workspace/ComfyUI
pip install -r requirements.txt
pip install -r custom_nodes/ComfyUI-Manager/requirements.txt
pip install -r custom_nodes/comfyui_controlnet_aux/requirements.txt
pip install -r custom_nodes/ComfyUI-Impact-Pack/requirements.txt
pip install -r custom_nodes/ComfyUI_IPAdapter_plus/requirements.txt

# Iniciar ComfyUI
echo "Iniciando ComfyUI..."
cd /workspace/ComfyUI
nohup python main.py --listen 0.0.0.0 --port 8188 --enable-cors-header > /workspace/logs/comfyui.log 2>&1 &
sleep 10

# Verificar se ComfyUI está rodando
if ! ps aux | grep -q "[p]ython.*ComfyUI"; then
    echo "[ERRO] ComfyUI não iniciou corretamente"
    exit 1
fi

# Iniciar API
echo "Iniciando API..."
cd /workspace/media-api2
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4 > /workspace/logs/api.log 2>&1 &

# Verificar se API está rodando
sleep 5
if ! ps aux | grep -q "[u]vicorn"; then
    echo "[ERRO] API não iniciou corretamente"
    exit 1
fi

echo "[$(date)] Setup concluído com sucesso!"

# Manter container rodando e monitorar logs
tail -f /workspace/logs/*.log