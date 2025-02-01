#!/bin/bash

MODELS_DIR="/workspace/ComfyUI/models"

# Função para download de modelo se não existir
download_if_not_exists() {
    local file_path=$1
    local url=$2
    local name=$3

    if [ ! -f "$file_path" ]; then
        echo "Downloading $name..."
        wget --progress=bar:force:noscroll -O "$file_path" "$url"
        echo "$name downloaded successfully!"
    else
        echo "$name already exists, skipping download."
    fi
}

# Criar diretórios se não existirem
mkdir -p "$MODELS_DIR"/{checkpoints,clip,clip_vision,controlnet,ipadapter,loras,upscale_models,vae}

# Download dos modelos SDXL
download_if_not_exists \
    "$MODELS_DIR/checkpoints/sd_xl_base_1.0.safetensors" \
    "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors" \
    "SDXL base model"

download_if_not_exists \
    "$MODELS_DIR/checkpoints/sd_xl_refiner_1.0.safetensors" \
    "https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors" \
    "SDXL refiner model"

download_if_not_exists \
    "$MODELS_DIR/vae/sdxl_vae.safetensors" \
    "https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors" \
    "SDXL VAE" 