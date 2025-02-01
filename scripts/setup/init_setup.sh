#!/bin/bash
set -e

echo "🚀 Iniciando setup automático do Media API..."

# Variáveis de configuração
DEFAULT_USER="admin"
DEFAULT_PASS="mediaapi2024"
DEFAULT_EMAIL="admin@mediaapi.com"
WORKSPACE="/workspace"
API_DIR="$WORKSPACE/media-api2"
COMFY_DIR="$WORKSPACE/ComfyUI"

# Detectar portas mapeadas
get_mapped_port() {
    local internal_port=$1
    local mapped_port=$(netstat -tlpn | grep ":$internal_port" | awk '{split($4,a,":"); print a[2]}')
    if [ -z "$mapped_port" ]; then
        echo "$internal_port"  # Fallback para porta original
    else
        echo "$mapped_port"
    fi
}

API_PORT=$(get_mapped_port 8000)
GUI_PORT=$(get_mapped_port 8080)
COMFY_PORT=$(get_mapped_port 8188)
REDIS_PORT=$(get_mapped_port 6379)

echo "Portas detectadas:"
echo "API: $API_PORT"
echo "GUI: $GUI_PORT"
echo "ComfyUI: $COMFY_PORT"
echo "Redis: $REDIS_PORT"

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}1. Instalando dependências...${NC}"
apt-get update && apt-get install -y \
    git python3-pip python3-venv redis-server net-tools ffmpeg \
    pkg-config libicu-dev python3-dev jq \
    python3-tk python3-dev python3-setuptools \
    libsm6 libxext6 libxrender-dev libglib2.0-0 \
    imagemagick

# Configurar imagemagick para permitir operações de vídeo
sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml || true
sed -i 's/rights="none" pattern="VIDEO"/rights="read|write" pattern="VIDEO"/' /etc/ImageMagick-6/policy.xml || true

echo -e "${BLUE}2. Configurando diretórios...${NC}"

# Criar grupo para a aplicação
groupadd -f mediaapi

# Adicionar usuário atual ao grupo
usermod -a -G mediaapi $(whoami)

mkdir -p $WORKSPACE/{logs,media,cache,models,config,temp} \
        $WORKSPACE/models/{lora,checkpoints,vae} \
        $WORKSPACE/media/{audio,images,video} \
        $WORKSPACE/temp \
        $WORKSPACE/outputs/suno \
        $WORKSPACE/cache/suno

# Definir propriedade dos diretórios (versão corrigida)
chown -R $(whoami):mediaapi \
    $WORKSPACE/temp \
    $WORKSPACE/outputs \
    $WORKSPACE/cache \
    $WORKSPACE/logs \
    $WORKSPACE/media \
    $WORKSPACE/models \
    $WORKSPACE/config

# Criar estrutura completa do projeto
echo "Criando estrutura de diretórios..."
mkdir -p $API_DIR/src/{api/{v1,v2},core,services,web,utils}
mkdir -p $API_DIR/src/core/cache
mkdir -p $API_DIR/src/generation/suno
mkdir -p $API_DIR/src/utils

# Criar __init__.py em todos os diretórios Python
find $API_DIR/src -type d -exec touch {}/__init__.py \;

# Criar estrutura básica de autenticação
mkdir -p $API_DIR/src/services
cat > $API_DIR/src/services/auth.py << 'EOF'
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Função que será importada por outros módulos
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Implementação básica
        return {"sub": "user"}  # Placeholder
    except JWTError:
        raise credentials_exception
EOF

# Criar arquivo vazio para endpoints/templates.py
touch $API_DIR/src/api/v2/endpoints/templates.py

# Verificar se os arquivos críticos existem
for file in \
    "src/main.py" \
    "src/services/auth.py" \
    "src/api/v2/endpoints/templates.py"; do
    if [ ! -f "$API_DIR/$file" ]; then
        echo "❌ Arquivo crítico não encontrado: $file"
        exit 1
    fi
done

# Ajustar PYTHONPATH
export PYTHONPATH=$API_DIR:$PYTHONPATH

echo -e "${BLUE}3. Configurando Redis...${NC}"
cat > /etc/redis/redis.conf << EOF
bind 127.0.0.1
port 6379
maxmemory 8gb
maxmemory-policy allkeys-lru
EOF

# Iniciar Redis diretamente
redis-server /etc/redis/redis.conf --daemonize yes

# Verificar se Redis iniciou
sleep 2
if ! redis-cli ping > /dev/null; then
    echo "Erro ao iniciar Redis!"
    exit 1
fi

echo -e "${BLUE}4. Configurando ambiente Python...${NC}"
python3 -m venv $WORKSPACE/venv_clean
. $WORKSPACE/venv_clean/bin/activate

echo -e "${BLUE}5. Instalando dependências Python...${NC}"
pip install --upgrade pip wheel setuptools || { echo "❌ Falha na instalação de pip"; exit 1; }

# Adicionar após o upgrade do pip
pip install ninja==1.11.1.1  # Necessário para compilação CUDA
pip install nvidia-ml-py==12.535.133  # Bindings Python para nvidia-smi

# Adicionar após cada bloco de instalação:
if [ $? -ne 0 ]; then
    echo "❌ Falha na instalação de dependências"
    exit 1
fi

# Instalar dependências críticas primeiro
pip install slowapi fastapi uvicorn redis aioredis itsdangerous starlette semver PyYAML gradio colorama python-slugify typing-extensions pydantic-settings

# Depois as dependências de mídia
pip install --no-cache-dir \
    moviepy==1.0.3 \
    opencv-python-headless==4.8.0.74 \
    ffmpeg-python==0.2.0 \
    Pillow==10.0.0 \
    numpy==1.24.0 \
    scipy==1.11.3 \
    einops==0.6.1 \
    pytorch-lightning==2.0.9 \
    aiofiles==23.2.1 \
    psutil==5.9.5

# Verificar instalação do moviepy
python -c "import moviepy.editor; print('Moviepy instalado com sucesso!')"

# Verificar versão do Python
python --version

# Adicionar antes da instalação do PyTorch
echo -e "${BLUE}Instalando CUDA Toolkit 12.1 e cuDNN...${NC}"
apt-get install -y --allow-change-held-packages \
    cuda-toolkit-12-1 \
    libcudnn8=8.9.7.29-1+cuda12.2

# E na instalação manual via .deb:
apt-get install -y --allow-change-held-packages libcudnn8=8.9.7.29-1+cuda12.2

# Atualizar variáveis de ambiente
sed -i 's/cuda-11.8/cuda-12.1/g' /etc/bash.bashrc
echo '[ -n "$BASH" ] && shopt -s histappend 2>/dev/null || true' >> /etc/bash.bashrc
. /etc/bash.bashrc

# Instalar torch primeiro
echo "Instalando PyTorch..."
pip install torch==2.1.0+cu121 torchvision==0.16.0+cu121 torchaudio==2.1.0+cu121 \
    --index-url https://download.pytorch.org/whl/cu121

# Instalar dependências do ComfyUI primeiro
echo "Instalando dependências do ComfyUI..."
cd $COMFY_DIR
pip install -r requirements.txt

# Iniciar ComfyUI em background
echo "Iniciando ComfyUI..."
nohup python main.py \
    --listen 0.0.0.0 \
    --port $COMFY_PORT \
    --disable-auto-launch \
    > /workspace/logs/comfyui.log 2>&1 &

# Depois as outras dependências
echo "Instalando dependências da API..."
cd $API_DIR
pip install -r $API_DIR/requirements/vast.txt
pip install -r $API_DIR/requirements.txt

# Verificar instalação
python -c "import torch; print(f'PyTorch instalado: {torch.__version__}')"
python -c "import fastapi; print(f'FastAPI instalado: {fastapi.__version__}')"

# Verificar todas as dependências críticas
echo "Verificando dependências críticas..."
python << EOF
import sys
try:
    import torch
    import fastapi
    import redis
    import uvicorn
    import PIL
    import moviepy.editor
    import cv2
    import numpy
    import einops
    import pytorch_lightning
    print("✅ Todas as dependências críticas estão instaladas")
except ImportError as e:
    print(f"❌ Erro ao importar dependências: {e}")
    sys.exit(1)
EOF

# Adicionar após a instalação do torch
pip install transformers==4.35.2

# Necessário para distribuição de modelos entre GPUs
pip install accelerate==0.25.0

# Adicionar na seção de dependências CUDA
pip install triton==2.1.0

# Adicionar após instalação do CUDA
pip install nvidia-cudnn-cu12==8.9.5.29 \
    nvidia-cublas-cu12==12.1.3.1 \
    nvidia-cuda-nvrtc-cu12==12.1.105 \
    nvidia-cuda-runtime-cu12==12.1.105

echo -e "${BLUE}Verificando drivers NVIDIA...${NC}"
nvidia-smi --query-gpu=driver_version --format=csv,noheader
if [ $? -ne 0 ]; then
    echo "❌ Drivers NVIDIA não detectados!"
    echo "Instale os drivers compatíveis com CUDA 12.1"
    exit 1
fi

echo -e "${BLUE}6. Iniciando serviços...${NC}"
cd $API_DIR

# Garantir que nenhuma instância antiga esteja rodando
pkill -f "uvicorn" || true
pkill -f "python main.py" || true

# Limpar arquivos temporários
rm -f /workspace/logs/api.log

# Iniciar API com log mais detalhado
echo "Iniciando API com um worker..."
export PYTHONPATH=$API_DIR:$PYTHONPATH
export LOG_LEVEL=debug

nohup uvicorn src.main:app \
    --host 0.0.0.0 \
    --port $API_PORT \
    --workers 1 \
    --log-level debug \
    --reload \
    --reload-dir src \
    > /workspace/logs/api.log 2>&1 &
API_PID=$!

# Log do processo
echo "PID da API: $API_PID"
ps -p $API_PID -o pid,ppid,cmd

# Aguardar API iniciar (com timeout)
echo "Aguardando API iniciar..."
MAX_TRIES=30
COUNT=0
while ! curl -s http://localhost:$API_PORT/health > /dev/null && [ $COUNT -lt $MAX_TRIES ]; do
    echo "Tentativa $((COUNT+1)) de $MAX_TRIES..."
    if ! ps -p $API_PID > /dev/null; then
        echo "Processo da API morreu! Verificando logs:"
        tail -n 50 /workspace/logs/api.log
        exit 1
    fi
    sleep 2
    COUNT=$((COUNT+1))

    # Mostrar logs em tempo real
    tail -n 5 /workspace/logs/api.log
done

if [ $COUNT -eq $MAX_TRIES ]; then
    echo "Erro: API não iniciou após $MAX_TRIES tentativas"
    echo "Últimas linhas do log:"
    tail -n 20 $WORKSPACE/logs/api.log
    exit 1
fi

echo "API iniciada com sucesso!"

echo -e "${BLUE}7. Criando usuário padrão...${NC}"
curl -X POST http://localhost:$API_PORT/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$DEFAULT_USER\",
    \"password\": \"$DEFAULT_PASS\",
    \"email\": \"$DEFAULT_EMAIL\",
    \"role\": \"admin\"
  }" || { echo "❌ Falha ao criar usuário"; exit 1; }

# Obter e salvar token
TOKEN=$(curl -s -X POST http://localhost:$API_PORT/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$DEFAULT_USER\",
    \"password\": \"$DEFAULT_PASS\"
  }" | jq -r '.access_token')

echo $TOKEN > $WORKSPACE/token.txt

echo -e "${GREEN}✅ Setup concluído!${NC}"
echo -e "Usuário: $DEFAULT_USER"
echo -e "Senha: $DEFAULT_PASS"
echo -e "Token salvo em: $WORKSPACE/token.txt"
echo -e "API rodando em: http://localhost:$API_PORT"
echo -e "GUI em: http://localhost:$GUI_PORT"
echo -e "ComfyUI em: http://localhost:$COMFY_PORT"

# Criar script de reinicialização
cat > $WORKSPACE/restart.sh << EOF
#!/bin/bash

echo "Reiniciando serviços..."

# Detectar portas novamente (podem ter mudado)
API_PORT=\$(netstat -tlpn | grep ":8000" | awk '{split(\$4,a,":"); print a[2]}')
API_PORT=\${API_PORT:-8000}  # Fallback para 8000 se não encontrar

. \$WORKSPACE/venv_clean/bin/activate

# Reiniciar Redis
pkill -f redis-server
redis-server /etc/redis/redis.conf --daemonize yes
sleep 2

if ! redis-cli ping > /dev/null; then
    echo "Erro ao reiniciar Redis!"
    exit 1
fi

# Reiniciar API
pkill -f "uvicorn"
cd $API_DIR
nohup uvicorn src.main:app --host 0.0.0.0 --port \$API_PORT --workers \$(nproc) > $WORKSPACE/logs/api.log 2>&1 &

# Reautenticar
sleep 5
TOKEN=\$(curl -s -X POST http://localhost:\$API_PORT/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "$DEFAULT_USER",
    "password": "$DEFAULT_PASS"
  }' | jq -r '.access_token')

echo \$TOKEN > $WORKSPACE/token.txt
echo "Serviços reiniciados! Novo token gerado."
echo "API rodando em: http://localhost:\$API_PORT"
EOF

chmod +x $WORKSPACE/restart.sh

# Criar arquivo de credenciais
cat > $WORKSPACE/credentials.txt << EOF
Usuário: $DEFAULT_USER
Senha: $DEFAULT_PASS
URL API: http://localhost:$API_PORT
URL GUI: http://localhost:$GUI_PORT
URL ComfyUI: http://localhost:$COMFY_PORT

Para reiniciar os serviços use:
./restart.sh

Para usar o token:
export TOKEN=$(cat /workspace/token.txt)
EOF

echo -e "${BLUE}Credenciais salvas em: $WORKSPACE/credentials.txt${NC}"

# Configurar variáveis de ambiente
cat > $WORKSPACE/.env << EOF
DEBUG=True
REDIS_HOST=localhost
REDIS_PORT=6379
JWT_SECRET_KEY=$TOKEN
JWT_ALGORITHM=HS256
RATE_LIMIT_PER_MINUTE=60
COMFY_API_URL=http://localhost:8188/api
COMFY_WS_URL=ws://localhost:8188/ws
MAX_CONCURRENT_RENDERS=4
MAX_RENDER_TIME=300
MAX_VIDEO_LENGTH=300
MAX_VIDEO_SIZE=100000000
RENDER_TIMEOUT_SECONDS=300
EOF

# Carregar variáveis
set -a
source $WORKSPACE/.env
set +a

# Criar arquivo de rate limiting
cat > $API_DIR/src/core/rate_limit.py << 'EOF'
"""
Módulo para controle de rate limiting usando Redis.
"""

from fastapi import Request, HTTPException, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.core.config import settings
import redis
import logging

logger = logging.getLogger(__name__)

# Configurar conexão Redis
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True
)

# Configurar limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
)

async def rate_limiter(request: Request):
    """
    Middleware para controle de rate limiting.
    
    Args:
        request: Request do FastAPI
        
    Raises:
        HTTPException: Se o limite de requisições for excedido
    """
    try:
        # Obter IP do cliente
        client_ip = get_remote_address(request)
        
        # Chave única para o cliente
        key = f"rate_limit:{client_ip}"
        
        # Verificar limite
        requests = redis_client.incr(key)
        
        # Se primeira requisição, definir TTL
        if requests == 1:
            redis_client.expire(key, 60)  # 60 segundos
            
        # Se excedeu limite
        if requests > settings.RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail="Too many requests"
            )
            
    except redis.RedisError as e:
        logger.error(f"Erro no Redis: {e}")
        # Em caso de erro no Redis, permite a requisição
        pass
    
    except Exception as e:
        logger.error(f"Erro no rate limiting: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
EOF

# Criar arquivo de gerenciamento de GPU
touch $API_DIR/src/core/gpu_manager.py

# Criar arquivos necessários
touch $API_DIR/src/core/queue_manager.py
touch $API_DIR/src/services/suno.py
touch $API_DIR/src/core/cache/manager.py
touch $API_DIR/src/utils/audio.py
touch $API_DIR/src/generation/suno/{bark_voice,musicgen}.py

# Substituir a chave fixa por uma gerada automaticamente
JWT_SECRET=$(openssl rand -hex 32)
sed -i "s/JWT_SECRET_KEY=your-secret-key-here/JWT_SECRET_KEY=$JWT_SECRET/" $WORKSPACE/.env

# Criar arquivo main.py básico se não existir
if [ ! -f "$API_DIR/src/main.py" ]; then
    cat > $API_DIR/src/main.py << 'EOF'
"""
Ponto de entrada principal da aplicação FastAPI
"""
from fastapi import FastAPI
from src.core.rate_limit import rate_limiter

app = FastAPI()
app.add_middleware(rate_limiter)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
EOF
fi

# Atualizar links para CUDA 12.1
ln -sfn /usr/local/cuda-12.1 /usr/local/cuda
ln -sfn /usr/local/cuda-12.1/lib64/libcudart.so.12.1 /usr/lib/x86_64-linux-gnu/libcudart.so.12.1

# Adicionar instalação do Bash
echo -e "${BLUE}Instalando Bash...${NC}"
apt-get install -y bash

# Modificar a linha problemática
sed -i 's/\[ -n "\$BASH" \] && shopt -s histappend/[ -n "$BASH" ] \&\& shopt -s histappend 2>\/dev\/null || true/' scripts/setup/init_setup.sh