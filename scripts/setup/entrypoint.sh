#!/bin/bash

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Configurações
WORKSPACE="/workspace"
API_DIR="$WORKSPACE/media-api2"
VENV_DIR="$WORKSPACE/venv_clean"
COMFY_DIR="$WORKSPACE/ComfyUI"

# Inicialização
log "Iniciando setup do Media API..."

# Configurar ambiente CUDA
export CUDA_HOME=/usr/local/cuda
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Limpar processos anteriores
log "Limpando processos anteriores..."
pkill -f "uvicorn" || true
pkill -f "redis-server" || true
pkill -f "python main.py" || true

# Limpar arquivos temporários
log "Limpando arquivos temporários..."
rm -rf "$WORKSPACE/tmp/"*
rm -f "$WORKSPACE/logs/api.log"

# Verificar GPUs
log "Verificando requisitos do sistema..."

# Função para verificar GPU
check_gpu() {
    if ! nvidia-smi > /dev/null 2>&1; then
        return 1
    fi
    local gpu_count
    gpu_count=$(nvidia-smi --query-gpu=gpu_name --format=csv,noheader | wc -l)
    if [ "$gpu_count" -eq 0 ]; then
        return 1
    fi
    return 0
}

# Verificar drivers NVIDIA
max_attempts=3
attempt=1
while [ $attempt -le $max_attempts ]; do
    if check_gpu; then
        break
    fi
    if [ $attempt -eq $max_attempts ]; then
        error "NVIDIA drivers não encontrados ou não funcionando após $max_attempts tentativas"
        nvidia-smi  # Debug output
        exit 1
    fi
    warn "Tentativa $attempt de $max_attempts - Aguardando drivers NVIDIA..."
    sleep 2
    attempt=$((attempt + 1))
done

# Mostrar informações das GPUs
NUM_GPUS=$(nvidia-smi --query-gpu=count --format=csv,noheader)
log "GPUs encontradas: $NUM_GPUS"
info "Informações detalhadas das GPUs:"
nvidia-smi --query-gpu=name,memory.total,driver_version,temperature.gpu --format=csv

# Criar diretórios necessários
log "Criando diretórios..."
directories=(
    "$WORKSPACE/tmp"
    "$WORKSPACE/logs"
    "$WORKSPACE/media"
    "$WORKSPACE/models"
    "$COMFY_DIR/models/checkpoints"
    "$COMFY_DIR/models/clip"
    "$COMFY_DIR/models/clip_vision"
    "$COMFY_DIR/models/controlnet"
    "$COMFY_DIR/models/ipadapter"
    "$COMFY_DIR/models/loras"
    "$COMFY_DIR/models/upscale_models"
    "$COMFY_DIR/models/vae"
)

for dir in "${directories[@]}"; do
    mkdir -p "$dir"
    chmod 755 "$dir"
    log "Diretório criado/ajustado: $dir"
done

# Configurar Redis
log "Configurando Redis..."
mkdir -p /etc/redis
cat > /etc/redis/redis.conf << EOF
bind 127.0.0.1
port 6379
maxmemory 8gb
maxmemory-policy allkeys-lru
daemonize yes
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
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
    warn "Tentativa $i/5 - Aguardando Redis..."
    sleep 1
done

# Verificar ambiente virtual
if [ ! -d "$VENV_DIR" ]; then
    log "Criando ambiente virtual..."
    python3.10 -m venv "$VENV_DIR"
fi

# Ativar ambiente virtual
source "$VENV_DIR/bin/activate"

# Verificar e instalar dependências
log "Verificando e instalando dependências..."
pip install --no-cache-dir -r requirements/base.txt

# Verificar instalação do aiohttp
python3 -c "import aiohttp" || {
    echo "Instalando aiohttp..."
    pip install --no-cache-dir aiohttp[speedups]
}

# Instalar dependências
log "Instalando dependências..."
pip install -r "$API_DIR/scripts/setup/requirements.txt"

# Instalar dependências do projeto
log "Instalando dependências do projeto..."
pip install -r "$API_DIR/requirements/vast.txt"

# Verificar dependências
log "Verificando dependências críticas..."
python "$API_DIR/scripts/check_models.py"

# Iniciar API
log "Iniciando API..."
cd "$API_DIR"
export PYTHONPATH="$API_DIR:$PYTHONPATH"
export LOG_LEVEL=info

# Iniciar monitor de GPU em background
cat > "$WORKSPACE/monitor.sh" << 'EOF'
#!/bin/bash
while true; do
    nvidia-smi >> /workspace/logs/gpu.log
    sleep 60
done
EOF
chmod +x "$WORKSPACE/monitor.sh"
nohup "$WORKSPACE/monitor.sh" &

# Verificar se uvicorn está instalado
if ! command -v uvicorn >/dev/null 2>&1; then
    error "uvicorn não encontrado. Instalando..."
    pip install --no-cache-dir uvicorn[standard]
fi

# Iniciar API com configurações otimizadas
python -m uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --loop uvloop \
    --http httptools \
    --log-level "$LOG_LEVEL"

log "Setup completo!"