#!/bin/bash

# Verifica se o Redis está instalado
if ! command -v redis-server &> /dev/null; then
    echo "Redis não encontrado. Instalando..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install redis
    elif [[ -f /etc/debian_version ]]; then
        # Debian/Ubuntu
        sudo apt-get update
        sudo apt-get install -y redis-server
    elif [[ -f /etc/redhat-release ]]; then
        # CentOS/RHEL
        sudo yum install -y redis
    else
        echo "Sistema operacional não suportado"
        exit 1
    fi
fi

# Verifica se o Redis já está rodando
if pgrep redis-server > /dev/null; then
    echo "Redis já está rodando"
    exit 0
fi

# Inicia o Redis
echo "Iniciando Redis..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    brew services start redis
else
    # Linux
    sudo systemctl start redis
fi

# Verifica se iniciou corretamente
sleep 2
if pgrep redis-server > /dev/null; then
    echo "Redis iniciado com sucesso"
    redis-cli ping
else
    echo "Erro ao iniciar Redis"
    exit 1
fi 