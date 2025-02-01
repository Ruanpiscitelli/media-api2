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

# Lista de diretórios para ajustar permissões
DIRECTORIES=(
    "/workspace"
    "/workspace/logs"
    "/workspace/media"
    "/workspace/tmp"
    "/workspace/models"
    "/workspace/ComfyUI"
    "/workspace/ComfyUI/models"
)

# Ajustar permissões
for dir in "${DIRECTORIES[@]}"; do
    if [ -d "$dir" ]; then
        log "Ajustando permissões para $dir"
        chmod -R 755 "$dir"
        chown -R $(whoami):$(whoami) "$dir"
    else
        log "Criando diretório $dir"
        mkdir -p "$dir"
        chmod -R 755 "$dir"
        chown -R $(whoami):$(whoami) "$dir"
    fi
done

# Verificar permissões
for dir in "${DIRECTORIES[@]}"; do
    if [ -d "$dir" ]; then
        perms=$(stat -c "%a %U:%G" "$dir")
        log "Permissões de $dir: $perms"
    fi
done

log "Permissões ajustadas com sucesso!" 