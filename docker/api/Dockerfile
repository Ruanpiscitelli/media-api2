"""
Dockerfile para a API com suporte a download automático de modelos.
"""

# syntax=docker/dockerfile:1

# Estágio de build
FROM python:3.11-slim as builder

# Instala dependências de build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cria e ativa ambiente virtual
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copia e instala requirements
COPY requirements/prod.txt .
RUN pip install --no-cache-dir -r prod.txt

# Estágio final
FROM python:3.11-slim

# Copia ambiente virtual do estágio de build
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instala CUDA e drivers NVIDIA
RUN apt-get update && apt-get install -y --no-install-recommends \
    cuda-toolkit-12-2 \
    nvidia-driver-535 \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root
RUN useradd -m -u 1000 appuser

# Configura diretório de trabalho
WORKDIR /app
COPY --chown=appuser:appuser . .

# Define variáveis de ambiente
ENV PYTHONPATH=/app
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,video

# Expõe porta da API
EXPOSE 8000

# Muda para usuário não-root
USER appuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando para iniciar a API
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"] 