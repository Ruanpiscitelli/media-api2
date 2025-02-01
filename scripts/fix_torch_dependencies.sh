#!/bin/bash

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Função para log
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Desativar ambiente virtual atual se existir
if [[ "$VIRTUAL_ENV" != "" ]]; then
    log "Desativando ambiente virtual atual..."
    deactivate
fi

# Recriar ambiente virtual do zero
log "Recriando ambiente virtual..."
rm -rf /workspace/venv_clean
python3.10 -m venv /workspace/venv_clean

# Ativar ambiente virtual
source /workspace/venv_clean/bin/activate

# Atualizar pip
log "Atualizando pip..."
python -m pip install --upgrade pip setuptools wheel

# Instalar PyTorch primeiro
log "Instalando PyTorch..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Instalar dependências críticas primeiro
log "Instalando dependências críticas..."
pip install --no-cache-dir \
    python-jose[cryptography] \
    redis \
    psutil \
    fastapi \
    uvicorn \
    python-dotenv \
    pydantic \
    pydantic-settings \
    aioredis \
    python-multipart \
    python-jose[cryptography] \
    passlib[bcrypt] \
    tenacity \
    prometheus-client \
    APScheduler

# Instalar dependências do projeto
log "Instalando dependências do projeto..."
pip install -r /workspace/media-api2/requirements/vast.txt --no-cache-dir

# Verificar instalações críticas
log "Verificando instalações..."
packages=(
    "torch"
    "python-jose"
    "redis"
    "psutil"
    "fastapi"
    "pydantic"
    "aioredis"
)

for package in "${packages[@]}"; do
    if python -c "import $package" 2>/dev/null; then
        log "✅ $package instalado com sucesso"
    else
        error "❌ Falha ao importar $package"
    fi
done

log "Setup completo!" 