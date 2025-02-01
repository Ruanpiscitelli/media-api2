#!/bin/bash

echo "🚀 Iniciando API..."

# 1. Verificar ambiente virtual
if [ ! -d "/workspace/venv_clean" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv /workspace/venv_clean
fi

source /workspace/venv_clean/bin/activate

# 2. Instalar/atualizar dependências
echo "Instalando dependências..."
pip install --upgrade pip wheel setuptools
pip install -r requirements/base.txt
pip install -r requirements.txt

# 3. Verificar Redis
echo "Verificando Redis..."
if ! service redis-server status > /dev/null; then
    echo "Iniciando Redis..."
    service redis-server start
fi

# 4. Configurar banco de dados
echo "Configurando banco de dados..."
export DATABASE_URL="sqlite:///./sql_app.db"
python3 -c "from src.core.db.init_db import init_db; init_db()"

# 5. Criar diretório de logs
mkdir -p /workspace/logs

# 6. Matar processos anteriores da API se existirem
pkill -f "uvicorn src.main:app"

# 7. Iniciar API com retry
MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Tentativa $((RETRY_COUNT+1)) de iniciar a API..."
    
    nohup uvicorn src.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 1 \
        --log-level debug \
        --reload \
        > /workspace/logs/api.log 2>&1 &
    
    # Aguardar API iniciar
    sleep 5
    
    # Verificar se está rodando
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "✅ API iniciada com sucesso!"
        break
    else
        echo "❌ Falha ao iniciar API, verificando logs..."
        tail -n 50 /workspace/logs/api.log
        ((RETRY_COUNT++))
        
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo "❌ Falha após $MAX_RETRIES tentativas"
            exit 1
        fi
        
        echo "Tentando novamente em 5 segundos..."
        sleep 5
    fi
done

# 8. Mostrar logs em tempo real
tail -f /workspace/logs/api.log 