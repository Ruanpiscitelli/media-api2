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

# Remover e recriar ambiente virtual
log "Recriando ambiente virtual..."
rm -rf /workspace/venv_clean
python3.10 -m venv /workspace/venv_clean

# Ativar novo ambiente virtual
source /workspace/venv_clean/bin/activate

# Atualizar pip
log "Atualizando pip..."
pip install --upgrade pip

# Instalar dependências básicas primeiro
log "Instalando dependências básicas..."
pip install --no-cache-dir \
    python-jose[cryptography] \
    psutil \
    fastapi \
    uvicorn \
    python-dotenv \
    pydantic \
    pydantic-settings

# Instalar outras dependências
log "Instalando dependências do projeto..."
pip install -r /workspace/media-api2/requirements/vast.txt --no-cache-dir

# Verificar instalação
log "Verificando instalações críticas..."
packages=(
    "python-jose"
    "cryptography"
    "psutil"
    "fastapi"
    "uvicorn"
    "pydantic"
)

for package in "${packages[@]}"; do
    if pip show "$package" > /dev/null; then
        log "✅ $package instalado"
    else
        error "❌ $package não encontrado"
    fi
done

log "Setup completo!" 