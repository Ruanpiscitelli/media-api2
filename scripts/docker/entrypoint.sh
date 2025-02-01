#!/bin/bash
set -e

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Variáveis de ambiente
WORKSPACE="/workspace"
API_DIR="$WORKSPACE/media-api"
COMFY_DIR="$WORKSPACE/ComfyUI"

# Função para log
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Função para verificar erro
check_error() {
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Erro: $1${NC}"
        exit 1
    fi
}

log "🚀 Iniciando setup do ambiente..."

# Verificar CUDA
log "📦 Verificando CUDA..."
nvidia-smi
check_error "CUDA não está disponível"

# Criar diretórios
log "📁 Criando estrutura de diretórios..."
mkdir -p $WORKSPACE/{logs,media,cache,models,config,temp} \
        $WORKSPACE/models/{lora,checkpoints,vae} \
        $WORKSPACE/media/{audio,images,video} \
        $WORKSPACE/temp \
        $WORKSPACE/outputs/suno \
        $WORKSPACE/cache/suno

# Configurar ambiente Python
log "🐍 Configurando ambiente Python..."
python3 -m venv $WORKSPACE/venv
source $WORKSPACE/venv/bin/activate

# Instalar dependências do sistema
log "📦 Instalando dependências do sistema..."
apt-get update && apt-get install -y \
    git python3-pip python3-venv redis-server net-tools ffmpeg \
    pkg-config libicu-dev python3-dev jq \
    python3-tk python3-dev python3-setuptools \
    libsm6 libxext6 libxrender-dev libglib2.0-0 \
    imagemagick ninja-build
check_error "Falha ao instalar dependências do sistema"

# Configurar imagemagick
sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml
sed -i 's/rights="none" pattern="VIDEO"/rights="read|write" pattern="VIDEO"/' /etc/ImageMagick-6/policy.xml

# Instalar dependências Python
log "📦 Instalando dependências Python..."
pip install --upgrade pip wheel setuptools
pip install ninja==1.11.1.1

# Instalar PyTorch com CUDA
log "🔥 Instalando PyTorch com CUDA..."
pip install torch==2.1.0+cu121 torchvision==0.16.0+cu121 torchaudio==2.1.0+cu121 \
    --index-url https://download.pytorch.org/whl/cu121
check_error "Falha ao instalar PyTorch"

# Instalar outras dependências
log "📚 Instalando dependências principais..."
pip install -r $API_DIR/requirements-dev.txt
check_error "Falha ao instalar dependências principais"

# Configurar Redis
log "🔄 Configurando Redis..."
cat > /etc/redis/redis.conf << EOF
bind 0.0.0.0
port 6379
maxmemory 8gb
maxmemory-policy allkeys-lru
EOF

# Gerar senha Redis
REDIS_PASSWORD=$(openssl rand -hex 32)
echo "requirepass $REDIS_PASSWORD" >> /etc/redis/redis.conf

# Iniciar Redis
log "🚀 Iniciando Redis..."
redis-server /etc/redis/redis.conf --daemonize yes
check_error "Falha ao iniciar Redis"

# Configurar variáveis de ambiente
log "⚙️ Configurando variáveis de ambiente..."
cat > $WORKSPACE/.env << EOF
DEBUG=True
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=$REDIS_PASSWORD
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
RATE_LIMIT_PER_MINUTE=60
COMFY_API_URL=http://localhost:8188/api
COMFY_WS_URL=ws://localhost:8188/ws
MAX_CONCURRENT_RENDERS=4
MAX_RENDER_TIME=300
MAX_VIDEO_LENGTH=300
MAX_VIDEO_SIZE=100000000
RENDER_TIMEOUT_SECONDS=300
REDIS_DB=0
REDIS_TIMEOUT=5
REDIS_SSL=false
EOF

# Carregar variáveis
set -a
source $WORKSPACE/.env
set +a

# Iniciar ComfyUI
if [ -d "$COMFY_DIR" ]; then
    log "🎨 Iniciando ComfyUI..."
    cd $COMFY_DIR
    nohup python main.py --listen 0.0.0.0 --port 8188 --disable-auto-launch > $WORKSPACE/logs/comfyui.log 2>&1 &
fi

# Iniciar API
log "🚀 Iniciando API..."
cd $API_DIR
export PYTHONPATH=$API_DIR:$PYTHONPATH

# Iniciar com Gunicorn para produção
gunicorn src.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --log-level debug \
    --access-logfile $WORKSPACE/logs/api_access.log \
    --error-logfile $WORKSPACE/logs/api_error.log \
    --capture-output \
    --daemon

# Iniciar GUI
log "🖥️ Iniciando GUI..."
gunicorn src.web.main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8080 \
    --log-level info \
    --access-logfile $WORKSPACE/logs/gui_access.log \
    --error-logfile $WORKSPACE/logs/gui_error.log \
    --capture-output \
    --daemon

# Verificar serviços
log "🔍 Verificando serviços..."
sleep 5

check_service() {
    if nc -z localhost $1; then
        echo -e "${GREEN}✅ $2 está rodando na porta $1${NC}"
    else
        echo -e "${RED}❌ $2 não está rodando na porta $1${NC}"
        tail -n 20 $WORKSPACE/logs/$3.log
        exit 1
    fi
}

check_service 8000 "API" "api"
check_service 8080 "GUI" "gui"
check_service 6379 "Redis" "redis"
[ -d "$COMFY_DIR" ] && check_service 8188 "ComfyUI" "comfyui"

log "✅ Todos os serviços iniciados com sucesso!"
echo -e """
${GREEN}🚀 Sistema pronto!${NC}

📌 Endpoints:
   API: http://localhost:8000
   GUI: http://localhost:8080
   Docs: http://localhost:8000/docs
   ComfyUI: http://localhost:8188

📝 Logs:
   API: tail -f $WORKSPACE/logs/api_*.log
   GUI: tail -f $WORKSPACE/logs/gui_*.log
   ComfyUI: tail -f $WORKSPACE/logs/comfyui.log
"""

# Manter container rodando
tail -f $WORKSPACE/logs/*.log 