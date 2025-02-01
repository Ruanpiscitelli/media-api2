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

# Verificar/Criar ComfyUI
if [ ! -d "/workspace/ComfyUI" ]; then
    log "ComfyUI não encontrado. Clonando repositório..."
    cd /workspace
    git clone https://github.com/comfyanonymous/ComfyUI.git
    cd ComfyUI
    pip install -r requirements.txt
fi

# Criar estrutura de diretórios do ComfyUI
COMFY_DIR="/workspace/ComfyUI"
MODELS_DIR="$COMFY_DIR/models"

# Criar todos os diretórios necessários
for dir in checkpoints clip clip_vision controlnet ipadapter loras upscale_models vae; do
    mkdir -p "$MODELS_DIR/$dir"
    if [ $? -eq 0 ]; then
        log "✅ Diretório $dir criado com sucesso"
    else
        error "❌ Falha ao criar diretório $dir"
        exit 1
    fi
done

# Verificar permissões
chmod -R 755 "$MODELS_DIR"

# URLs dos modelos
SDXL_BASE_URL="https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors"
SDXL_REFINER_URL="https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors"
SDXL_VAE_URL="https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/vae.safetensors"

# Download função com retry
download_model() {
    local url=$1
    local output=$2
    local name=$3
    local max_retries=3
    local retry=0
    
    while [ $retry -lt $max_retries ]; do
        log "Downloading $name (tentativa $((retry+1))/$max_retries)..."
        if wget --no-verbose --show-progress -c -O "$output" "$url"; then
            log "✅ $name downloaded successfully!"
            return 0
        else
            error "❌ Falha no download de $name"
            ((retry++))
            if [ $retry -lt $max_retries ]; then
                log "Tentando novamente em 5 segundos..."
                sleep 5
            fi
        fi
    done
    
    error "❌ Falha após $max_retries tentativas de download de $name"
    return 1
}

# Download dos modelos
models_to_download=(
    "$SDXL_BASE_URL|$MODELS_DIR/checkpoints/sd_xl_base_1.0.safetensors|SDXL base model"
    "$SDXL_REFINER_URL|$MODELS_DIR/checkpoints/sd_xl_refiner_1.0.safetensors|SDXL refiner model"
    "$SDXL_VAE_URL|$MODELS_DIR/vae/sdxl_vae.safetensors|SDXL VAE"
)

for model in "${models_to_download[@]}"; do
    IFS="|" read -r url output name <<< "$model"
    if [ ! -f "$output" ]; then
        download_model "$url" "$output" "$name"
    else
        log "✅ $name já existe, pulando download"
    fi
done

# Atualizar .env
log "Atualizando arquivo .env..."
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

log "Verificando instalação..."
python scripts/check_models.py

log "Setup completo!" 