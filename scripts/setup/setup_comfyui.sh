#!/bin/bash

COMFY_DIR="/workspace/ComfyUI"
LOG_FILE="/workspace/logs/comfyui_setup.log"

# Função para logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Criar diretório de logs se não existir
mkdir -p "$(dirname "$LOG_FILE")"

# Verificar se ComfyUI já existe
if [ ! -d "$COMFY_DIR" ]; then
    log "Clonando ComfyUI..."
    git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFY_DIR"
else
    log "ComfyUI já existe, atualizando..."
    cd "$COMFY_DIR" || exit 1
    git pull
fi

# Entrar no diretório do ComfyUI
cd "$COMFY_DIR" || exit 1

# Criar estrutura de diretórios
log "Criando estrutura de diretórios..."
directories=(
    "models/checkpoints"
    "models/clip"
    "models/clip_vision"
    "models/controlnet"
    "models/ipadapter"
    "models/loras"
    "models/upscale_models"
    "models/vae"
    "input"
    "output"
)

for dir in "${directories[@]}"; do
    mkdir -p "$dir"
    log "Criado diretório: $dir"
done

# Instalar dependências
log "Instalando dependências do ComfyUI..."
pip install -r requirements.txt

# Verificar instalação
log "Verificando instalação..."
python -c "import torch; print(f'PyTorch instalado: {torch.__version__}')"
python -c "import torchvision; print(f'TorchVision instalado: {torchvision.__version__}')"

log "Setup do ComfyUI concluído!" 