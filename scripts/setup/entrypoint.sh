#!/bin/bash

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
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

# Inicialização
log "Iniciando setup do Media API..."

# Limpar arquivos temporários
log "Limpando arquivos temporários..."
rm -rf /workspace/tmp/*

# Matar processos anteriores
log "Limpando processos anteriores..."
pkill -f "uvicorn"
pkill -f "redis-server"

# Verificar GPUs
log "Verificando requisitos do sistema..."
if ! command -v nvidia-smi &> /dev/null; then
    error "NVIDIA drivers não encontrados"
    exit 1
fi

# Mostrar informações das GPUs
NUM_GPUS=$(nvidia-smi --query-gpu=count --format=csv,noheader)
log "GPUs encontradas: $NUM_GPUS"

log "Informações das GPUs:"
echo "name, memory.total [MiB], driver_version"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

# Configurar Redis
log "Configurando Redis..."
cat > /etc/redis/redis.conf << EOF
bind 127.0.0.1
port 6379
maxmemory 8gb
maxmemory-policy allkeys-lru
EOF

# Iniciar Redis
log "Iniciando Redis..."
redis-server /etc/redis/redis.conf --daemonize yes

# Verificar Redis
log "Verificando Redis..."
for i in {1..5}; do
    if redis-cli ping > /dev/null; then
        log "Redis conectado"
        break
    fi
    if [ $i -eq 5 ]; then
        error "Falha ao conectar ao Redis"
        exit 1
    fi
    warn "Tentando conectar ao Redis (tentativa $i/5)..."
    sleep 1
done

# Iniciar API
log "Iniciando API..."
cd /workspace/media-api2
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4

log "Setup completo!"