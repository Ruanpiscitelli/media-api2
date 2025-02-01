#!/bin/bash

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Função para log
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Estrutura de diretórios padrão do ComfyUI
COMFY_DIR="/workspace/ComfyUI"
MODELS_DIR="$COMFY_DIR/models"

# Criar estrutura de diretórios do ComfyUI
mkdir -p "$MODELS_DIR"/{checkpoints,clip,clip_vision,controlnet,ipadapter,loras,upscale_models,vae}

# URLs dos modelos
SDXL_BASE_URL="https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors"
SDXL_REFINER_URL="https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors"
SDXL_VAE_URL="https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/vae.safetensors"

# Download função
download_model() {
    local url=$1
    local output=$2
    local name=$3
    
    log "Downloading $name..."
    if wget -q --show-progress -O "$output" "$url"; then
        log "$name downloaded successfully!"
    else
        error "Failed to download $name"
        return 1
    fi
}

# Download modelos para os diretórios padrão do ComfyUI
download_model "$SDXL_BASE_URL" "$MODELS_DIR/checkpoints/sd_xl_base_1.0.safetensors" "SDXL base model"
download_model "$SDXL_REFINER_URL" "$MODELS_DIR/checkpoints/sd_xl_refiner_1.0.safetensors" "SDXL refiner model"
download_model "$SDXL_VAE_URL" "$MODELS_DIR/vae/sdxl_vae.safetensors" "SDXL VAE"

# Atualizar .env com os caminhos corretos do ComfyUI
cat > /workspace/media-api2/.env << EOF
DEBUG=True
ENVIRONMENT=development

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Caminhos dos modelos (usando estrutura do ComfyUI)
SDXL_MODEL_PATH=$MODELS_DIR/checkpoints/sd_xl_base_1.0.safetensors
SDXL_VAE_PATH=$MODELS_DIR/vae/sdxl_vae.safetensors
FISH_SPEECH_MODEL=$MODELS_DIR/checkpoints/fish_speech_model.pt

# Diretórios
MEDIA_DIR=/workspace/media
MODELS_DIR=$MODELS_DIR
TEMP_DIR=/workspace/tmp
LOGS_DIR=/workspace/logs

# API
HOST=0.0.0.0
PORT=8000
WORKERS=4
EOF

log "Setup completo!" 