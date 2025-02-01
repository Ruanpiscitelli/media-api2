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
pkill -f "uvicorn" || true
pkill -f "redis-server" || true

# Verificar GPUs
log "Verificando requisitos do sistema..."
if ! nvidia-smi &> /dev/null; then
    error "NVIDIA drivers não encontrados ou não funcionando"
    exit 1
fi

# Mostrar informações das GPUs
if ! NUM_GPUS=$(nvidia-smi --query-gpu=count --format=csv,noheader 2>/dev/null); then
    error "Falha ao obter contagem de GPUs"
    exit 1
fi

log "GPUs encontradas: $NUM_GPUS"

# Verificar se há GPUs disponíveis
if [ "$NUM_GPUS" -eq 0 ]; then
    error "Nenhuma GPU encontrada"
    exit 1
fi

log "Informações das GPUs:"
echo "name, memory.total [MiB], driver_version"
if ! nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader; then
    error "Falha ao obter informações das GPUs"
    exit 1
fi

# Criar diretórios necessários
log "Criando diretórios..."
mkdir -p /workspace/{tmp,logs,media,models}

# Configurar Redis
log "Configurando Redis..."
mkdir -p /etc/redis
cat > /etc/redis/redis.conf << EOF
bind 127.0.0.1
port 6379
maxmemory 8gb
maxmemory-policy allkeys-lru
daemonize yes
EOF

# Iniciar Redis
log "Iniciando Redis..."
redis-server /etc/redis/redis.conf

# Verificar Redis
log "Verificando Redis..."
for i in {1..5}; do
    if redis-cli ping > /dev/null 2>&1; then
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

# Verificar ambiente virtual
if [ ! -d "/workspace/venv_clean" ]; then
    log "Criando ambiente virtual..."
    python3.10 -m venv /workspace/venv_clean
fi

# Ativar ambiente virtual
source /workspace/venv_clean/bin/activate

# Iniciar API
log "Iniciando API..."
cd /workspace/media-api2
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4

log "Setup completo!"