# Use CUDA base image
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

# Evitar prompts durante a instalação
ENV DEBIAN_FRONTEND=noninteractive

# Definir variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV COMFY_DIR=/opt/ComfyUI
ENV WORKSPACE_DIR=/workspace

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3.10-venv \
    git \
    wget \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Criar e ativar ambiente virtual
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Clonar ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git ${COMFY_DIR}

# Instalar dependências Python
WORKDIR ${COMFY_DIR}
RUN pip install --no-cache-dir torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121
RUN pip install --no-cache-dir -r requirements.txt

# Instalar dependências adicionais
RUN pip install --no-cache-dir \
    transformers \
    accelerate \
    safetensors \
    xformers \
    triton \
    opencv-python-headless \
    pillow \
    aiohttp \
    pydantic \
    prometheus-client

# Criar diretórios necessários
RUN mkdir -p ${WORKSPACE_DIR}/models/stable-diffusion \
    ${WORKSPACE_DIR}/models/lora \
    ${WORKSPACE_DIR}/models/vae \
    ${WORKSPACE_DIR}/models/embeddings \
    ${WORKSPACE_DIR}/outputs

# Copiar arquivos de configuração
COPY config.yaml ${COMFY_DIR}/config.yaml
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Expor porta
EXPOSE 8188

# Definir volume para modelos e outputs
VOLUME ${WORKSPACE_DIR}

# Comando de inicialização
CMD ["/start.sh"] 