#!/bin/bash

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

WORKSPACE="/workspace"
API_DIR="$WORKSPACE/media-api2"
LOG_DIR="$WORKSPACE/logs"

echo -e "${BLUE}🔍 Verificando serviços...${NC}"

# Função para verificar se um serviço está rodando
check_service() {
    local port=$1
    local name=$2
    if netstat -tuln | grep -q ":$port "; then
        echo -e "${GREEN}✅ $name está rodando na porta $port${NC}"
        return 0
    else
        echo -e "${RED}❌ $name não está rodando na porta $port${NC}"
        return 1
    fi
}

# Verificar Redis
echo -e "\n${BLUE}Verificando Redis...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis está respondendo${NC}"
else
    echo -e "${RED}❌ Redis não está respondendo${NC}"
    echo "Iniciando Redis..."
    redis-server /etc/redis/redis.conf --daemonize yes
    sleep 2
fi

# Ativar ambiente virtual
echo -e "\n${BLUE}Ativando ambiente virtual...${NC}"
if [ -f "$WORKSPACE/venv_clean/bin/activate" ]; then
    source $WORKSPACE/venv_clean/bin/activate
    echo -e "${GREEN}✅ Ambiente virtual ativado${NC}"
else
    echo -e "${RED}❌ Ambiente virtual não encontrado${NC}"
    exit 1
fi

# Verificar dependências críticas
echo -e "\n${BLUE}Verificando dependências Python...${NC}"
python << EOF
import sys
try:
    import torch
    import fastapi
    import redis
    import uvicorn
    print("✅ Dependências críticas OK")
except ImportError as e:
    print(f"❌ Erro: {e}")
    sys.exit(1)
EOF

# Iniciar API
echo -e "\n${BLUE}Iniciando API...${NC}"
mkdir -p $LOG_DIR

# Matar processos anteriores
pkill -f "uvicorn" || true

# Configurar variáveis
export PYTHONPATH=$API_DIR:$PYTHONPATH
export LOG_LEVEL=debug

# Iniciar API com log
cd $API_DIR
nohup uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir src \
    > $LOG_DIR/api.log 2>&1 &

API_PID=$!

# Aguardar API iniciar
echo "Aguardando API iniciar..."
MAX_TRIES=15
COUNT=0

while [ $COUNT -lt $MAX_TRIES ]; do
    echo -n "."
    if curl -s http://localhost:8000/health > /dev/null; then
        echo -e "\n${GREEN}✅ API iniciada com sucesso!${NC}"
        break
    fi
    
    # Verificar se processo morreu
    if ! ps -p $API_PID > /dev/null; then
        echo -e "\n${RED}❌ Processo da API morreu!${NC}"
        echo -e "\nÚltimas linhas do log:"
        tail -n 20 $LOG_DIR/api.log
        exit 1
    fi
    
    sleep 2
    COUNT=$((COUNT+1))
    
    # Mostrar erros do log
    if [ $COUNT -eq $MAX_TRIES ]; then
        echo -e "\n${RED}❌ API não iniciou após várias tentativas${NC}"
        echo -e "\nÚltimas linhas do log:"
        tail -n 20 $LOG_DIR/api.log
        exit 1
    fi
done

# Verificar todos os serviços
echo -e "\n${BLUE}Status final dos serviços:${NC}"
check_service 8000 "API"
check_service 6379 "Redis"
check_service 8188 "ComfyUI"

echo -e "\n${BLUE}URLs:${NC}"
echo "API: http://localhost:8000"
echo "ComfyUI: http://localhost:8188"

echo -e "\n${BLUE}Logs:${NC}"
echo "API: $LOG_DIR/api.log"
echo "ComfyUI: $LOG_DIR/comfyui.log"

echo -e "\n${GREEN}✨ Pronto!${NC}" 