# Base image do RunPod
FROM --platform=linux/amd64 runpod/stable-diffusion:web-ui-13.0.0

# Instalar dependências adicionais
RUN apt-get update && apt-get install -y \
    redis-server \
    net-tools \
    ffmpeg \
    git-lfs \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Configurar diretórios
WORKDIR /workspace

# Clonar repositórios
RUN git clone https://github.com/Ruanpiscitelli/media-api2.git && \
    git clone https://github.com/comfyanonymous/ComfyUI.git

# Criar requirements
RUN mkdir -p /workspace/media-api2/requirements
COPY requirements/vast.txt /workspace/media-api2/requirements/

# Configurar ComfyUI
WORKDIR /workspace/ComfyUI
RUN mkdir -p custom_nodes && \
    cd custom_nodes && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git && \
    git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git && \
    git clone https://github.com/pythongosssss/ComfyUI-Custom-Scripts.git && \
    git clone https://github.com/ltdrdata/ComfyUI-Impact-Pack.git && \
    git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git

# Criar diretórios de modelos (vazios)
RUN mkdir -p models/{checkpoints,clip,clip_vision,controlnet,ipadapter,loras,upscale_models,vae}

# Usar o ambiente Python existente do RunPod
ENV PATH="/opt/conda/bin:$PATH"

# Instalar dependências Python
WORKDIR /workspace/media-api2
RUN pip install -r requirements/vast.txt

# Instalar dependências do ComfyUI
WORKDIR /workspace/ComfyUI
RUN pip install -r requirements.txt || true && \
    for req in custom_nodes/*/requirements.txt; do \
        if [ -f "$req" ]; then \
            echo "Installing requirements from $req" && \
            pip install -r "$req" || true; \
        fi \
    done

# Configurar frontend
WORKDIR /workspace/media-api2/frontend

# Instalar dependências do Node.js e build
RUN npm install -g npm@latest && \
    npm install && \
    npm run build

# Criar diretório para logs
RUN mkdir -p /workspace/logs

# Copiar scripts
COPY scripts/startup.sh /workspace/
COPY scripts/download_models.sh /workspace/
RUN chmod +x /workspace/startup.sh /workspace/download_models.sh

# Expor portas
EXPOSE 8000 8188 6379

# Iniciar serviços
CMD ["/workspace/startup.sh"] 