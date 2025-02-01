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

# Instalar python-jose separadamente
log "Instalando python-jose..."
pip install --no-cache-dir python-jose[cryptography]

# Verificar instalações
log "Verificando instalações..."
python -c "import torch; print(f'PyTorch {torch.__version__} instalado com sucesso')"
python -c "from jose import jwt; print('python-jose instalado com sucesso')"

log "Setup completo!" 