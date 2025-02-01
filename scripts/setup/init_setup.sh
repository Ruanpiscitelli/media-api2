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

# Verificar versão do Python
python --version

# Instalar torch primeiro
echo "Instalando PyTorch..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Instalar dependências do ComfyUI primeiro
echo "Instalando dependências do ComfyUI..."
cd $COMFY_DIR
pip install -r requirements.txt

# Depois as outras dependências
echo "Instalando dependências da API..."
cd $API_DIR
pip install -r $API_DIR/requirements/vast.txt
pip install -r $API_DIR/requirements.txt

# Verificar instalação
python -c "import torch; print(f'PyTorch instalado: {torch.__version__}')"
python -c "import fastapi; print(f'FastAPI instalado: {fastapi.__version__}')"

echo -e "${BLUE}6. Iniciando serviços...${NC}"
cd $API_DIR

# Garantir que nenhuma instância antiga esteja rodando
pkill -f "uvicorn" || true

# Iniciar API com log mais detalhado
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers $(nproc) > $WORKSPACE/logs/api.log 2>&1 &

# Aguardar API iniciar (com timeout)
echo "Aguardando API iniciar..."
MAX_TRIES=30
COUNT=0
while ! curl -s http://localhost:8000/health > /dev/null && [ $COUNT -lt $MAX_TRIES ]; do
    echo "Tentativa $((COUNT+1)) de $MAX_TRIES..."
    sleep 2
    COUNT=$((COUNT+1))
done

if [ $COUNT -eq $MAX_TRIES ]; then
    echo "Erro: API não iniciou após $MAX_TRIES tentativas"
    echo "Últimas linhas do log:"
    tail -n 20 $WORKSPACE/logs/api.log
    exit 1
fi

echo "API iniciada com sucesso!"

echo -e "${BLUE}7. Criando usuário padrão...${NC}"
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$DEFAULT_USER\",
    \"password\": \"$DEFAULT_PASS\",
    \"email\": \"$DEFAULT_EMAIL\",
    \"role\": \"admin\"
  }"

# Obter e salvar token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
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
echo -e "API rodando em: http://localhost:8000"
echo -e "GUI em: http://localhost:8080"

# Criar script de reinicialização
cat > $WORKSPACE/restart.sh << EOF
#!/bin/bash

echo "Reiniciando serviços..."

. $WORKSPACE/venv_clean/bin/activate

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
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers \$(nproc) > $WORKSPACE/logs/api.log 2>&1 &

# Reautenticar
sleep 5
TOKEN=\$(curl -s -X POST http://localhost:8000/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "$DEFAULT_USER",
    "password": "$DEFAULT_PASS"
  }' | jq -r '.access_token')

echo \$TOKEN > $WORKSPACE/token.txt
echo "Serviços reiniciados! Novo token gerado."
EOF

chmod +x $WORKSPACE/restart.sh

# Criar arquivo de credenciais
cat > $WORKSPACE/credentials.txt << EOF
Usuário: $DEFAULT_USER
Senha: $DEFAULT_PASS
URL API: http://localhost:8000
URL GUI: http://localhost:8080

Para reiniciar os serviços use:
./restart.sh

Para usar o token:
export TOKEN=\$(cat /workspace/token.txt)
EOF

echo -e "${BLUE}Credenciais salvas em: $WORKSPACE/credentials.txt${NC}" 