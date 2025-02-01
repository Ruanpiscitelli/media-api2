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

# Instalar dependências
log "Instalando dependências..."
pip install -r /workspace/media-api2/requirements/vast.txt

# Ajustar permissões sem sudo (já que estamos como root)
log "Ajustando permissões..."

# Criar diretórios com permissões corretas
directories=(
    "/workspace"
    "/workspace/logs"
    "/workspace/media"
    "/workspace/tmp"
    "/workspace/models"
    "/workspace/ComfyUI"
    "/workspace/ComfyUI/models"
)

for dir in "${directories[@]}"; do
    mkdir -p "$dir"
    chmod 777 "$dir"  # Dar permissões totais
    log "Diretório $dir criado/ajustado"
done

# Verificar permissões
log "\nVerificando permissões finais:"
for dir in "${directories[@]}"; do
    if [ -d "$dir" ]; then
        perms=$(stat -c "%a %U:%G" "$dir")
        log "$dir: $perms"
    fi
done

# Criar arquivo .env se não existir
if [ ! -f "/workspace/media-api2/.env" ]; then
    log "Criando arquivo .env..."
    cat > /workspace/media-api2/.env << EOF
DEBUG=True
ENVIRONMENT=development
EOF
fi

log "Setup completo!"