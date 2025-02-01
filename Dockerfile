# Atualizar imagem base e versão do CUDA
FROM nvidia/cuda:12.2.0-base-ubuntu22.04

# Adicionar OpenTelemetry e monitoramento
RUN apt-get update && apt-get install -y \
    ocl-icd-opencl-dev \
    libgl1 \
    libglib2.0-0 \
    opentelemetry-sdk

# Configurar NVLink
ENV NVIDIA_DISABLE_REQUIRE=1
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV NVIDIA_VISIBLE_DEVICES=all

# Instalar dependências adicionais
RUN apt-get update && apt-get install -y \
    redis-server \
    net-tools \
    ffmpeg \
    git-lfs \
    nodejs \
    npm \
    git \
    python3-pip \
    python3-dev \
    pkg-config \
    libicu-dev \
    cuda-nvlink-12-2 \
    libnvidia-nvlink1 \
    cuda-toolkit-12-2 \
    libnvidia-compute-525 \
    && rm -rf /var/lib/apt/lists/*

# Configurar diretórios
WORKDIR /workspace

# Copiar seu projeto
COPY . /workspace/media-api2/

# Clonar ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git

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

# Instalar dependências Python
WORKDIR /workspace/media-api2
RUN python3 -m venv /workspace/venv_clean && \
    /workspace/venv_clean/bin/pip install --upgrade pip wheel setuptools && \
    /workspace/venv_clean/bin/pip install -r requirements/vast.txt && \
    /workspace/venv_clean/bin/pip install -r requirements.txt

WORKDIR /workspace/ComfyUI
RUN pip install -r requirements.txt || true && \
    for req in custom_nodes/*/requirements.txt; do \
        if [ -f "$req" ]; then \
            echo "Installing requirements from $req" && \
            pip install -r "$req" || true; \
        fi \
    done

# Criar diretório para logs
RUN mkdir -p /workspace/logs

# Script de inicialização simples
RUN echo '#!/bin/sh\n\
redis-server --daemonize yes\n\
cd /workspace/ComfyUI && python main.py --listen 0.0.0.0 --port 8188 --enable-cors-header > /workspace/logs/comfyui.log 2>&1 &\n\
cd /workspace/media-api2 && python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4 > /workspace/logs/api.log 2>&1 &\n\
tail -f /workspace/logs/*.log' > /workspace/start.sh && chmod +x /workspace/start.sh

# Expor portas
EXPOSE 8000 8188 6379

# Copiar entrypoint
COPY scripts/setup/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Configurar variáveis de ambiente para NVLink
ENV NCCL_DEBUG=INFO
ENV NCCL_NET_GDR_LEVEL=5

# Instalar dependências adicionais
RUN pip install torch==2.2.0+cu122 torchvision==0.17.0+cu122 torchaudio==2.2.0+cu122

# Comando de inicialização
ENTRYPOINT ["/entrypoint.sh"]