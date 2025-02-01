#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Função para log
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Configurar ambiente
setup_environment() {
    log "Configurando ambiente..."
    
    # Verificar Python
    if ! command -v python3.10 &> /dev/null; then
        log "Instalando Python 3.10..."
        apt-get update
        apt-get install -y python3.10 python3.10-venv python3.10-dev
    fi
    
    # Criar diretórios necessários
    mkdir -p /workspace/venv_clean
    mkdir -p /workspace/logs
    mkdir -p /workspace/media
    mkdir -p /workspace/models
    mkdir -p /workspace/cache
    
    # Criar ambiente virtual
    python3.10 -m venv /workspace/venv_clean
    
    # Ativar ambiente virtual
    source /workspace/venv_clean/bin/activate
    
    # Atualizar pip
    python -m pip install --upgrade pip
    
    # Instalar dependências
    log "Instalando dependências..."
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
    pip install -r /workspace/media-api2/requirements/vast.txt
    
    # Criar arquivo .env se não existir
    if [ ! -f "/workspace/media-api2/.env" ]; then
        log "Criando arquivo .env..."
        cat > /workspace/media-api2/.env << EOF
DEBUG=True
ENVIRONMENT=development
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
EOF
    fi
}

# Executar setup
setup_environment

log "Ambiente configurado com sucesso!"
log "Para ativar o ambiente virtual, execute:"
log "source /workspace/venv_clean/bin/activate" 