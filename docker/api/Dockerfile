"""
Dockerfile para a API com suporte a download automático de modelos.
"""

# syntax=docker/dockerfile:1

FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Evitar prompts durante instalação
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    ffmpeg \
    redis-server \
    espeak-ng \
    espeak-ng-data \
    libespeak-ng-dev \
    curl \
    git \
    software-properties-common \
    libx264-dev \
    libx265-dev \
    libvpx-dev \
    libopus-dev \
    libmp3lame-dev \
    libfdk-aac-dev \
    python3-dev \
    gcc \
    libc-dev \
    net-tools \
    git-lfs \
    nodejs \
    npm \
    python3-pip \
    pkg-config \
    libicu-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && add-apt-repository ppa:savoury1/ffmpeg4 \
    && apt-get update \
    && apt-get install -y \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root
RUN useradd -m -u 1000 appuser

# Criar diretórios necessários
RUN mkdir -p /workspace/logs /workspace/media /workspace/cache \
    && chown -R appuser:appuser /workspace

# Mudar para usuário não-root
USER appuser
WORKDIR /workspace/media-api2

# Configurar ambiente Python
ENV PYTHONPATH=/workspace/media-api2
ENV VIRTUAL_ENV=/workspace/venv_clean
RUN python3.11 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Instalar dependências Python
COPY --chown=appuser:appuser requirements/ requirements/
COPY --chown=appuser:appuser requirements.txt .
COPY requirements/base.txt /app/requirements/base.txt
RUN pip install --no-cache-dir -r requirements/vast.txt \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r /app/requirements/base.txt

# Copiar código
COPY --chown=appuser:appuser . .

# Instalar PyTorch com versão noturna se necessário
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/nightly/cu121

# Adicionar Redis
RUN apt-get update && apt-get install -y \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Copiar configuração do Redis
COPY config/redis.conf /etc/redis/redis.conf

# Garantir que o Redis inicie
CMD ["bash", "-c", "service redis-server start && uvicorn src.main:app --host 0.0.0.0 --port 8000"]

# Script de entrada
ENTRYPOINT ["./scripts/setup/entrypoint.sh"] 