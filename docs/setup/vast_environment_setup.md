# Configuração do Media API na Vast.ai via Terminal

Este guia explica como configurar o Media API (https://github.com/Ruanpiscitelli/media-api2) na Vast.ai usando a imagem aidockorg/comfyui-cuda como base.

## Pré-requisitos

- Conta na Vast.ai
- Acesso SSH
- Git configurado

## 1. Configuração na Vast.ai

1. Acesse https://vast.ai/console/create/
2. Configure a instância:
   - Imagem: `aidockorg/comfyui-cuda:latest`
   - GPU: RTX 4090 (1-4x)
   - RAM: Mínimo 32GB
   - Disco: 100GB
   - Portas: 8000,8188,6379,8080
   - Selecione "Enable SSH"

## 2. Script de Configuração

Após conectar via SSH, crie o arquivo setup.sh:

```bash
cat > setup.sh << 'EOF'
#!/bin/bash
set -e

echo "Iniciando configuração do Media API..."

# Configuração do sistema
apt-get update && apt-get install -y \
    git python3-pip python3-venv redis-server net-tools ffmpeg \
    nvidia-cuda-toolkit nvidia-cuda-toolkit-gcc \
    pkg-config libicu-dev python3-dev

# Estrutura de diretórios
mkdir -p /workspace/{logs,media,cache,models,config,temp} \
        /workspace/models/{lora,checkpoints,vae} \
        /workspace/media/{audio,images,video}

# Clone do repositório
git clone https://github.com/Ruanpiscitelli/media-api2.git /workspace/media-api2

# Ambiente Python
python3 -m venv /workspace/venv_clean
source /workspace/venv_clean/bin/activate

# Atualizar pip e instalar ferramentas básicas
pip install --upgrade pip wheel setuptools

# Remover instalações existentes para evitar conflitos
pip uninstall -y fastapi gradio uvicorn apscheduler

# Dependências CUDA
pip install -r requirements/vast.txt

# Verificar instalação do ComfyUI
cd /workspace/ComfyUI
python -c "import folder_paths" || pip install -r requirements.txt

# Dependências do projeto
cd /workspace/media-api2
pip install -r requirements.txt

# Configuração do Redis
cat > /etc/redis/redis.conf << REDISCONF
bind 127.0.0.1
port 6379
maxmemory 8gb
maxmemory-policy allkeys-lru
REDISCONF

# Configurar variáveis de ambiente
cat > /workspace/.env << ENVFILE
NVIDIA_VISIBLE_DEVICES=all
DATA_DIRECTORY=/workspace
API_HOST=0.0.0.0
API_PORT=8000
REDIS_HOST=localhost
REDIS_PORT=6379
COMFY_HOST=0.0.0.0
COMFY_PORT=8188
MEDIA_DIR=/workspace/media
MODELS_DIR=/workspace/models
ENVFILE

# Iniciar serviços
service redis-server restart

# Configurar logs
mkdir -p /workspace/logs
touch /workspace/logs/{api,redis,gpu}.log

# Iniciar API com múltiplos workers
cd /workspace/media-api2
source /workspace/venv_clean/bin/activate
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers $(nproc) \
    --log-level info --log-file /workspace/logs/api.log &

# Script de monitoramento
cat > /workspace/monitor.sh << 'MONITOREOF'
#!/bin/bash
while true; do
    echo "\n=== GPU Status ===" >> /workspace/logs/gpu.log
    nvidia-smi >> /workspace/logs/gpu.log
    sleep 60
done
MONITOREOF

chmod +x /workspace/monitor.sh
nohup /workspace/monitor.sh &

echo "Configuração concluída!"
EOF

chmod +x setup.sh
```

## 3. Execução e Deploy

1. Conecte-se via SSH:
```bash
ssh root@<ip> -p <porta>
```

2. Execute o script:
```bash
cd /workspace
./setup.sh
```

## 4. Verificação e Monitoramento

1. Verifique os serviços:
```bash
# Status da API
curl localhost:8000/health

# Logs da API
tail -f /workspace/logs/api.log

# Status do Redis
redis-cli ping

# Monitoramento GPU
nvidia-smi
```

2. Teste os endpoints:
```bash
# Primeiro, obtenha o token de autenticação
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "seu_usuario", "password": "sua_senha"}' \
  | jq -r '.access_token' > token.txt

# Guarde o token em uma variável
TOKEN=$(cat token.txt)

# Teste de áudio com autenticação
curl -X POST http://localhost:8000/api/v1/audio/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"text": "teste", "voice_id": "1"}'

# Teste de imagem com autenticação
curl -X POST http://localhost:8000/api/v1/image/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"prompt": "teste"}'
```

## 5. Comandos Úteis

```bash
# Reiniciar serviços
service redis-server restart
pkill -f uvicorn
cd /workspace/media-api2 && \
source /workspace/venv_clean/bin/activate && \
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers $(nproc) &

# Limpar cache
redis-cli FLUSHALL
rm -rf /workspace/cache/*

# Backup rápido
tar -czf /workspace/backup_$(date +%Y%m%d).tar.gz \
    /workspace/media-api2/config \
    /workspace/models \
    /workspace/media

# Monitoramento
watch -n1 nvidia-smi
tail -f /workspace/logs/*.log
```

## 6. Solução de Problemas

1. **Verificar Status:**
```bash
# Processos
ps aux | grep uvicorn
ps aux | grep redis

# Portas
netstat -tulpn

# GPU
nvidia-smi
```

2. **Problemas Comuns:**
```bash
# Erro de CUDA
python3 -c "import torch; print(torch.cuda.is_available())"

# Erro de memória
free -h
redis-cli info | grep used_memory_human

# Logs de erro
tail -f /workspace/logs/api.log
```

3. **Reiniciar Tudo:**
```bash
# Parar serviços
pkill -f uvicorn
service redis-server stop

# Limpar
redis-cli FLUSHALL
rm -rf /workspace/cache/*

# Reiniciar
service redis-server start
cd /workspace/media-api2 && \
source /workspace/venv_clean/bin/activate && \
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers $(nproc) &
```

## Autenticação e Tokens

### 1. Criar Usuário Inicial
```bash
# Crie um usuário administrativo
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "senha_segura",
    "email": "admin@exemplo.com",
    "role": "admin"
  }'
```

### 2. Login e Obtenção do Token
```bash
# Login e salvar token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "senha_segura"
  }' | jq -r '.access_token' > token.txt

# Usar token em requisições
TOKEN=$(cat token.txt)
```

### 3. Exemplo de Script para Requisições
```bash
#!/bin/bash

# Configurações
API_URL="http://localhost:8000"
USERNAME="admin"
PASSWORD="senha_segura"

# Login e obtenção do token
TOKEN=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
  | jq -r '.access_token')

# Função para fazer requisições autenticadas
make_request() {
    local endpoint=$1
    local data=$2
    
    curl -s -X POST "$API_URL$endpoint" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d "$data"
}

# Exemplos de uso
# Gerar áudio
make_request "/api/v1/audio/generate" \
  '{"text":"teste de audio","voice_id":"1"}'

# Gerar imagem
make_request "/api/v1/image/generate" \
  '{"prompt":"teste de imagem"}'
```

### 4. Renovação do Token
```bash
# Renovar token expirado
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Verificar Status do Token
```bash
# Verificar se o token é válido
curl http://localhost:8000/api/v1/auth/verify \
  -H "Authorization: Bearer $TOKEN"
```

## Referências

- [Media API Documentation](https://github.com/Ruanpiscitelli/media-api2)
- [ComfyUI Docker Image](https://hub.docker.com/r/aidockorg/comfyui-cuda)
- [Vast.ai Documentation](https://vast.ai/docs/)

## 8. Persistência e Backup

### Backup Automático
```bash
# Criar script de backup
cat > /workspace/backup.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/workspace/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Criar diretório de backup
mkdir -p $BACKUP_DIR

# Backup de configurações e dados
tar -czf $BACKUP_DIR/media_api_$DATE.tar.gz \
    /workspace/media-api2/config \
    /workspace/models \
    /workspace/media \
    /workspace/.env \
    /etc/redis/redis.conf

# Manter apenas os últimos 5 backups
ls -t $BACKUP_DIR/media_api_*.tar.gz | tail -n +6 | xargs -r rm

# Backup do Redis
redis-cli save
cp /var/lib/redis/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Log do backup
echo "Backup completo: $DATE" >> /workspace/logs/backup.log
EOF

chmod +x /workspace/backup.sh

# Adicionar ao crontab
(crontab -l 2>/dev/null; echo "0 */6 * * * /workspace/backup.sh") | crontab -
```

### Monitoramento Avançado
```bash
# Criar script de monitoramento
cat > /workspace/monitor_advanced.sh << 'EOF'
#!/bin/bash

LOG_FILE="/workspace/logs/monitor.log"

check_service() {
    if ! systemctl is-active --quiet $1; then
        echo "$(date): $1 está inativo. Tentando reiniciar..." >> $LOG_FILE
        systemctl restart $1
    fi
}

check_gpu() {
    if ! nvidia-smi > /dev/null 2>&1; then
        echo "$(date): Problema com GPU detectado" >> $LOG_FILE
        systemctl restart media-api
    fi
}

check_memory() {
    MEM_FREE=$(free | grep Mem | awk '{print $4/$2 * 100.0}')
    if (( $(echo "$MEM_FREE < 10" | bc -l) )); then
        echo "$(date): Memória baixa ($MEM_FREE%). Limpando cache..." >> $LOG_FILE
        sync; echo 3 > /proc/sys/vm/drop_caches
        redis-cli FLUSHALL
    fi
}

while true; do
    check_service media-api
    check_service redis-server
    check_gpu
    check_memory
    sleep 300
done
EOF

chmod +x /workspace/monitor_advanced.sh
```

### Criar Serviço de Monitoramento Avançado
```bash
cat > /etc/systemd/system/monitor-advanced.service << 'EOF'
[Unit]
Description=Advanced Monitoring Service
After=network.target

[Service]
Type=simple
User=root
ExecStart=/workspace/monitor_advanced.sh
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable monitor-advanced
systemctl start monitor-advanced
```

### Recuperação de Falhas
```bash
# Criar script de recuperação
cat > /workspace/recovery.sh << 'EOF'
#!/bin/bash

# Função para restaurar backup
restore_backup() {
    LATEST_BACKUP=$(ls -t /workspace/backups/media_api_*.tar.gz | head -n1)
    if [ -n "$LATEST_BACKUP" ]; then
        systemctl stop media-api redis-server
        tar -xzf $LATEST_BACKUP -C /
        systemctl start redis-server media-api
        echo "Backup restaurado: $LATEST_BACKUP"
    fi
}

# Função para limpar e reiniciar
clean_restart() {
    systemctl stop media-api redis-server
    redis-cli FLUSHALL
    rm -rf /workspace/cache/*
    systemctl start redis-server media-api
    echo "Sistema limpo e reiniciado"
}

# Menu de recuperação
case "$1" in
    "backup")
        restore_backup
        ;;
    "clean")
        clean_restart
        ;;
    *)
        echo "Uso: ./recovery.sh [backup|clean]"
        ;;
esac
EOF

chmod +x /workspace/recovery.sh
```

### Verificação de Saúde
```bash
# Criar script de verificação
cat > /workspace/healthcheck.sh << 'EOF'
#!/bin/bash

check_endpoint() {
    local endpoint=$1
    local response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000$endpoint)
    echo "Endpoint $endpoint: $response"
}

echo "=== Verificação de Saúde do Sistema ==="
echo "Status dos Serviços:"
systemctl status media-api --no-pager
systemctl status redis-server --no-pager

echo -e "\nEndpoints da API:"
check_endpoint "/health"
check_endpoint "/metrics"

echo -e "\nStatus da GPU:"
nvidia-smi

echo -e "\nUso de Memória:"
free -h

echo -e "\nUso de Disco:"
df -h /workspace
EOF

chmod +x /workspace/healthcheck.sh
```

## 9. Procedimento Pós-Reinicialização

### Passo a Passo após Reiniciar
```bash
# 1. Conecte-se via SSH
ssh root@<ip> -p <porta>

# 2. Ative o ambiente virtual
source /workspace/venv_clean/bin/activate

# 3. Verifique se o Redis está rodando
service redis-server status
# Se não estiver: service redis-server start

# 4. Inicie a API
cd /workspace/media-api2
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers $(nproc) &

# 5. Verifique se está funcionando
curl localhost:8000/health

# 6. Faça login novamente para obter um novo token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "senha_segura"
  }' | jq -r '.access_token' > token.txt

# 7. Configure o token para uso
TOKEN=$(cat token.txt)
```

### Script de Reinicialização Rápida
```bash
cat > /workspace/restart.sh << 'EOF'
#!/bin/bash

echo "Iniciando serviços..."

# Ativar ambiente virtual
source /workspace/venv_clean/bin/activate

# Iniciar Redis se não estiver rodando
if ! service redis-server status > /dev/null; then
    echo "Iniciando Redis..."
    service redis-server start
fi

# Verificar se a API já está rodando
if pgrep -f "uvicorn src.main:app" > /dev/null; then
    echo "API já está rodando. Reiniciando..."
    pkill -f "uvicorn src.main:app"
fi

# Iniciar API
cd /workspace/media-api2
echo "Iniciando API..."
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers $(nproc) > /workspace/logs/api.log 2>&1 &

# Aguardar API iniciar
echo "Aguardando API iniciar..."
sleep 5

# Verificar saúde
if curl -s localhost:8000/health > /dev/null; then
    echo "API está funcionando!"
    
    # Obter novo token
    echo "Obtendo novo token..."
    TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
      -H "Content-Type: application/json" \
      -d '{"username":"admin","password":"senha_segura"}' \
      | jq -r '.access_token')
    
    if [ ! -z "$TOKEN" ]; then
        echo $TOKEN > /workspace/token.txt
        echo "Novo token salvo em /workspace/token.txt"
    else
        echo "Erro ao obter token"
    fi
else
    echo "Erro: API não está respondendo"
fi
EOF

chmod +x /workspace/restart.sh
```

### Uso do Script de Reinicialização
```bash
# Após reiniciar o servidor, simplesmente execute:
/workspace/restart.sh

# Para usar o token nas requisições:
TOKEN=$(cat /workspace/token.txt)
```

## 10. Inicialização Automática

### Configurar Serviços Systemd
```bash
# 1. Criar serviço para a API
cat > /etc/systemd/system/media-api.service << 'EOF'
[Unit]
Description=Media API Service
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=/workspace/media-api2
Environment="PATH=/workspace/venv_clean/bin:$PATH"
ExecStartPre=/bin/bash -c 'source /workspace/venv_clean/bin/activate'
ExecStart=/workspace/venv_clean/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers $(nproc)
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 2. Criar script de autenticação automática
cat > /workspace/auto_auth.sh << 'EOF'
#!/bin/bash

# Aguardar API iniciar
sleep 10

# Tentar autenticação
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"senha_segura"}' \
  | jq -r '.access_token')

if [ ! -z "$TOKEN" ]; then
    echo $TOKEN > /workspace/token.txt
    echo "Token atualizado automaticamente"
fi
EOF

chmod +x /workspace/auto_auth.sh

# 3. Criar serviço para autenticação automática
cat > /etc/systemd/system/auto-auth.service << 'EOF'
[Unit]
Description=Automatic Authentication Service
After=media-api.service

[Service]
Type=oneshot
User=root
ExecStart=/workspace/auto_auth.sh

[Install]
WantedBy=multi-user.target
EOF

# 4. Habilitar todos os serviços
systemctl daemon-reload
systemctl enable redis-server
systemctl enable media-api
systemctl enable auto-auth
systemctl enable monitor-advanced

# 5. Iniciar serviços
systemctl start redis-server
systemctl start media-api
systemctl start auto-auth
systemctl start monitor-advanced
```

### Verificar Status dos Serviços Automáticos
```bash
# Verificar status de todos os serviços
systemctl status redis-server
systemctl status media-api
systemctl status auto-auth
systemctl status monitor-advanced

# Verificar logs
journalctl -u media-api -f
journalctl -u auto-auth -f
```

### Testar Reinicialização Automática
```bash
# Simular reinicialização
sudo reboot

# Após reiniciar, verificar se tudo está funcionando
curl localhost:8000/health

# Verificar se o token foi gerado
cat /workspace/token.txt
```

## Acessando a GUI

### Método 1: Via Vast.ai Dashboard
1. Acesse https://vast.ai/console/instances/
2. Encontre sua instância
3. Procure pela porta 8080 nos "exposed ports"
4. Clique no link fornecido ou use a URL: `http://[ip-instance]:[port]`

### Método 2: Via Túnel SSH
```bash
# Criar túnel SSH
ssh -L 8080:localhost:8080 root@[ip-instance] -p [porta-ssh]

# Agora acesse no navegador:
# http://localhost:8080
```

### Endpoints Disponíveis
- `/` - Página inicial com documentação
- `/auth` - Página de autenticação
- `/endpoints/[seção]` - Documentação específica de cada seção
  - `/endpoints/auth` - Autenticação
  - `/endpoints/comfy` - ComfyUI
  - `/endpoints/image` - Geração de Imagem
  - `/endpoints/video` - Geração de Vídeo
  - `/endpoints/speech` - Síntese de Voz
  - `/endpoints/system` - Sistema
