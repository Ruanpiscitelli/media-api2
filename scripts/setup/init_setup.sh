#!/usr/bin/env bash
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
    pkg-config libicu-dev python3-dev jq

echo -e "${BLUE}2. Configurando diretórios...${NC}"
mkdir -p $WORKSPACE/{logs,media,cache,models,config,temp} \
        $WORKSPACE/models/{lora,checkpoints,vae} \
        $WORKSPACE/media/{audio,images,video}

# Criar diretórios necessários para a web
mkdir -p $API_DIR/src/web/{templates,static/css,utils}

# Verificar arquivos críticos
for file in \
    "src/main.py" \
    "src/web/routes.py" \
    "src/web/templates/base.html" \
    "requirements.txt" \
    "requirements/vast.txt"; do
    if [ ! -f "$API_DIR/$file" ]; then
        echo "❌ Arquivo crítico não encontrado: $file"
        exit 1
    fi
done

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
pip install --upgrade pip wheel setuptools

# Instalar dependências críticas primeiro
pip install slowapi fastapi uvicorn redis itsdangerous starlette semver PyYAML gradio colorama python-slugify typing-extensions pydantic-settings

# Verificar versão do Python
python --version

# Instalar torch primeiro
echo "Instalando PyTorch..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

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
    print("✅ Todas as dependências críticas estão instaladas")
except ImportError as e:
    print(f"❌ Erro ao importar dependências: {e}")
    sys.exit(1)
EOF

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
  }"

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
NVIDIA_VISIBLE_DEVICES=all
DATA_DIRECTORY=/workspace
API_HOST=0.0.0.0
API_PORT=$API_PORT
REDIS_HOST=localhost
REDIS_PORT=$REDIS_PORT
COMFY_HOST=0.0.0.0
COMFY_PORT=$COMFY_PORT
MEDIA_DIR=/workspace/media
MODELS_DIR=/workspace/models
EOF

# Carregar variáveis
set -a
source $WORKSPACE/.env
set +a

# Criar estrutura básica de autenticação
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

# Criar __init__.py nos diretórios necessários
touch $API_DIR/src/services/__init__.py
touch $API_DIR/src/api/__init__.py
touch $API_DIR/src/api/v1/__init__.py
touch $API_DIR/src/api/v2/__init__.py
touch $API_DIR/src/api/v1/endpoints/__init__.py
touch $API_DIR/src/api/v2/endpoints/__init__.py 