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

# Configurar e iniciar Redis como serviço
cat > /etc/systemd/system/redis-server.service << EOF
[Unit]
Description=Redis In-Memory Data Store
After=network.target

[Service]
Type=forking
ExecStart=/usr/bin/redis-server /etc/redis/redis.conf
PIDFile=/run/redis/redis-server.pid
TimeoutStopSec=0
Restart=always
User=redis
Group=redis

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable redis-server
systemctl start redis-server

echo -e "${BLUE}4. Configurando ambiente Python...${NC}"
python3 -m venv $WORKSPACE/venv_clean
source $WORKSPACE/venv_clean/bin/activate

echo -e "${BLUE}5. Instalando dependências Python...${NC}"
pip install --upgrade pip wheel setuptools
pip install -r $API_DIR/requirements.txt
pip install -r $API_DIR/requirements/vast.txt

echo -e "${BLUE}6. Iniciando serviços...${NC}"
cd $API_DIR
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers $(nproc) > $WORKSPACE/logs/api.log 2>&1 &

# Aguardar API iniciar
sleep 5

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

source $WORKSPACE/venv_clean/bin/activate

# Reiniciar Redis
systemctl restart redis-server

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