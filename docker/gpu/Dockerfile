FROM nvidia/cuda:12.2.0-base-ubuntu22.04

# Instalar dependências do sistema em uma única camada
RUN apt-get update && apt-get install -y \
    ffmpeg \
    python3-dev \
    gcc \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Configurar ambiente Python
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Copiar e instalar requirements primeiro para melhor cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf ~/.cache/pip

# Criar diretórios necessários
RUN mkdir -p /workspace/models/fish_speech \
    /workspace/media \
    /workspace/logs \
    /workspace/cache

# Copiar código da aplicação
COPY . .

# Script de healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando para iniciar a aplicação
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Copiar script de download
COPY scripts/download_models.py /app/scripts/

# Criar diretório de modelos e baixar
RUN mkdir -p /workspace/models && \
    python /app/scripts/download_models.py

# ... resto do Dockerfile ... 