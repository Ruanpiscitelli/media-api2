#!/bin/bash

# Criar diretórios necessários
mkdir -p /workspace/logs
mkdir -p /workspace/ComfyUI/models/{checkpoints,clip,clip_vision,controlnet,ipadapter,loras,upscale_models,vae}

# Clonar repositórios
cd /workspace
git clone https://github.com/Ruanpiscitelli/media-api2.git
git clone https://github.com/comfyanonymous/ComfyUI.git

# Instalar dependências
cd /workspace/media-api2
pip install -r requirements/vast.txt

# Configurar ComfyUI
cd /workspace/ComfyUI
pip install -r requirements.txt

# Download dos modelos (opcional - pode ser feito depois)
/workspace/download_models.sh

# Iniciar serviços
/workspace/startup.sh 