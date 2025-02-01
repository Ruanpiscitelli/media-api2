#!/bin/bash

# Verificar se os diretórios necessários existem
for dir in models/stable-diffusion models/lora models/vae models/embeddings outputs; do
    if [ ! -d "${WORKSPACE_DIR}/${dir}" ]; then
        echo "Criando diretório ${WORKSPACE_DIR}/${dir}"
        mkdir -p "${WORKSPACE_DIR}/${dir}"
    fi
done

# Verificar se há modelos base disponíveis
if [ -z "$(ls -A ${WORKSPACE_DIR}/models/stable-diffusion)" ]; then
    echo "AVISO: Nenhum modelo base encontrado em ${WORKSPACE_DIR}/models/stable-diffusion"
    echo "Por favor, adicione pelo menos um modelo SDXL base neste diretório"
fi

# Configurar links simbólicos para os modelos
ln -sf ${WORKSPACE_DIR}/models/stable-diffusion ${COMFY_DIR}/models/stable-diffusion
ln -sf ${WORKSPACE_DIR}/models/lora ${COMFY_DIR}/models/lora
ln -sf ${WORKSPACE_DIR}/models/vae ${COMFY_DIR}/models/vae
ln -sf ${WORKSPACE_DIR}/models/embeddings ${COMFY_DIR}/models/embeddings
ln -sf ${WORKSPACE_DIR}/outputs ${COMFY_DIR}/output

# Iniciar o servidor ComfyUI
cd ${COMFY_DIR}
python main.py --listen 0.0.0.0 --port 8188 --cuda-device 0 