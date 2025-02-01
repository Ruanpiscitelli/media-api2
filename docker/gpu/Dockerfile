FROM nvidia/cuda:12.2.0-base-ubuntu22.04

# ... outras configurações ...

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    libpq-dev \
    python3-dev \
    gcc \
    postgresql-client \
    espeak \
    espeak-ng \
    libespeak-ng1 \
    # ... outras dependências ...

# Instalar dependências Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copiar script de download
COPY scripts/download_models.py /app/scripts/

# Criar diretório de modelos e baixar
RUN mkdir -p /workspace/models && \
    python /app/scripts/download_models.py

# ... resto do Dockerfile ... 