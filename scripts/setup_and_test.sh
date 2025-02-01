#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Iniciando setup do Media API...${NC}"

# Verificar se Python 3.10+ está instalado
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$python_version 3.10" | awk '{print ($1 < $2)}') )); then
    echo -e "${RED}❌ Python 3.10+ é necessário. Versão atual: $python_version${NC}"
    exit 1
fi

# Criar e ativar ambiente virtual
echo -e "${YELLOW}📦 Criando ambiente virtual...${NC}"
python3 -m venv venv
source venv/bin/activate

# Função para verificar e instalar dependências
setup_dependencies() {
    echo -e "${YELLOW}📦 Verificando dependências...${NC}"
    
    # Lista de pacotes essenciais
    local packages=(
        # Framework e Servidor
        "fastapi>=0.100.0"
        "uvicorn>=0.15.0"
        "python-multipart>=0.0.5"
        "python-jose[cryptography]>=3.3.0"
        "passlib[bcrypt]>=1.7.4"
        "itsdangerous>=2.0.0"
        "starlette>=0.27.0"
        "pydantic-settings>=2.0.0"
        
        # Agendamento e Cache
        "APScheduler>=3.10.1"
        "redis>=4.0.0"
        "aioredis>=2.0.0"
        
        # Monitoramento
        "prometheus-client>=0.14.0"
        "slowapi>=0.1.8"
        "opentelemetry-api>=1.0.0"
        "opentelemetry-sdk>=1.0.0"
        "opentelemetry-instrumentation-fastapi==0.41b0"
        
        # Processamento de Mídia
        "moviepy>=1.0.3"
        "opencv-python-headless>=4.8.0.74"
        "ffmpeg-python>=0.2.0"
        "Pillow>=10.0.0"
        "numpy>=1.24.0"
        "scipy>=1.11.3"
        
        # AI e ML
        "torch>=2.0.0"
        "torchvision>=0.15.0"
        "torchaudio>=2.0.0"
        "transformers>=4.35.2"
        "diffusers>=0.19.0"
        "accelerate>=0.25.0"
        "safetensors>=0.3.1"
        "einops>=0.6.1"
        "pytorch-lightning>=2.0.9"
        
        # Utilitários
        "python-dotenv>=1.0.0"
        "pydantic>=2.0.0"
        "aiofiles>=23.0.0"
        "websockets>=10.0"
        "psutil>=5.9.0"
        "requests>=2.31.0"
        "typing-extensions>=4.5.0"
        "PyYAML>=6.0.0"
        "gradio>=4.19.1"
        "colorama>=0.4.6"
        "python-slugify>=8.0.0"
        "yt-dlp>=2023.11.16"
        "ninja>=1.11.1.1"
        "nvidia-ml-py>=12.535.133"
        
        # CUDA e GPU
        "nvidia-cudnn-cu12>=8.9.7.29"
        "nvidia-cublas-cu12>=12.1.3.1"
        "nvidia-cuda-nvrtc-cu12>=12.1.105"
        "nvidia-cuda-runtime-cu12>=12.1.105"
        "triton>=2.1.0"
    )
    
    # Instalar pip-tools se não estiver instalado
    pip install --upgrade pip pip-tools

    echo -e "${YELLOW}📥 Instalando dependências principais...${NC}"
    
    # Criar requirements-dev.txt atualizado
    echo "# Gerado automaticamente por setup_and_test.sh" > requirements-dev.txt
    for package in "${packages[@]}"; do
        echo "$package" >> requirements-dev.txt
    done
    
    # Instalar dependências
    pip install -r requirements-dev.txt || {
        echo -e "${RED}❌ Falha ao instalar dependências via requirements.txt${NC}"
        echo -e "${YELLOW}🔄 Tentando instalar pacotes essenciais individualmente...${NC}"
        
        for package in "${packages[@]}"; do
            echo -e "${YELLOW}📦 Instalando $package...${NC}"
            pip install "$package" || {
                echo -e "${RED}❌ Falha ao instalar $package${NC}"
                return 1
            }
        done
    }
    
    # Verificar instalação do PyTorch com CUDA
    python -c "import torch; print(f'PyTorch instalado com CUDA: {torch.cuda.is_available()}')" || {
        echo -e "${RED}❌ Erro na instalação do PyTorch com CUDA${NC}"
        return 1
    }
    
    # Verificar todas as dependências críticas
    echo -e "${YELLOW}✅ Verificando dependências críticas...${NC}"
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
    import yt_dlp
    print("✅ Todas as dependências críticas estão instaladas")
except ImportError as e:
    print(f"❌ Erro ao importar dependências: {e}")
    sys.exit(1)
EOF
    
    echo -e "${GREEN}✅ Todas as dependências instaladas com sucesso${NC}"
    return 0
}

# Substituir a parte de instalação de dependências por:
echo -e "${YELLOW}📚 Configurando dependências...${NC}"
setup_dependencies || {
    echo -e """
${RED}❌ Falha ao configurar dependências.${NC}

${YELLOW}🔍 Tente manualmente:${NC}
1. pip install -r requirements.txt
2. pip install apscheduler fastapi uvicorn redis

${YELLOW}📊 Status das dependências:${NC}
$(pip list | grep -E 'fastapi|uvicorn|redis|apscheduler')
"""
    exit 1
}

# Verificar e iniciar Redis
setup_redis() {
    echo -e "${YELLOW}🔄 Configurando Redis...${NC}"
    
    # Verificar se Redis está instalado
    if ! command -v redis-cli &> /dev/null; then
        echo -e "${YELLOW}📦 Instalando Redis...${NC}"
        brew install redis || {
            echo -e "${RED}❌ Falha ao instalar Redis${NC}"
            return 1
        }
    fi
    
    # Parar qualquer instância existente
    brew services stop redis 2>/dev/null
    
    # Iniciar Redis
    echo -e "${YELLOW}🚀 Iniciando Redis...${NC}"
    brew services start redis || {
        echo -e "${RED}❌ Falha ao iniciar Redis${NC}"
        return 1
    }
    
    # Aguardar Redis iniciar
    echo -e "${YELLOW}⏳ Aguardando Redis iniciar...${NC}"
    for i in {1..10}; do
        if redis-cli ping &>/dev/null; then
            echo -e "${GREEN}✅ Redis está rodando${NC}"
            return 0
        fi
        sleep 1
    done
    
    echo -e "${RED}❌ Timeout aguardando Redis iniciar${NC}"
    return 1
}

# Verificar Redis
echo -e "${YELLOW}🔄 Verificando Redis...${NC}"
setup_redis || {
    echo -e """
${RED}❌ Falha ao configurar Redis.${NC}

${YELLOW}🔍 Tente manualmente:${NC}
1. brew services stop redis
2. brew services start redis
3. redis-cli ping

${YELLOW}📊 Status atual:${NC}
$(brew services list | grep redis)

${YELLOW}🔍 Logs do Redis:${NC}
$(tail -n 20 /usr/local/var/log/redis.log 2>/dev/null || echo "Logs não encontrados")
"""
    exit 1
}

# Criar diretórios necessários
echo -e "${YELLOW}📁 Criando diretórios...${NC}"
mkdir -p logs
mkdir -p temp
mkdir -p workflows
mkdir -p outputs

# Adicionar após a criação dos diretórios básicos:

echo -e "${YELLOW}📁 Criando estrutura de diretórios completa...${NC}"
mkdir -p {logs,media,cache,models,config,temp}
mkdir -p models/{lora,checkpoints,vae}
mkdir -p media/{audio,images,video}
mkdir -p temp
mkdir -p outputs/suno
mkdir -p cache/suno

# Ajustar permissões
chmod -R 755 {logs,media,cache,models,config,temp}

# Função para mostrar últimas linhas do log
show_log() {
    local log_file=$1
    local service=$2
    echo -e "${YELLOW}📝 Últimas linhas do log do $service:${NC}"
    if [ -f "$log_file" ]; then
        tail -n 20 "$log_file"
    else
        echo -e "${RED}Arquivo de log não encontrado: $log_file${NC}"
    fi
}

# Função para verificar se um serviço está rodando
check_service() {
    local port=$1
    local service=$2
    local log_file=$3
    if nc -z localhost $port; then
        echo -e "${GREEN}✅ $service está rodando na porta $port${NC}"
        return 0
    else
        echo -e "${RED}❌ $service não está rodando na porta $port${NC}"
        if [ ! -z "$log_file" ]; then
            show_log "$log_file" "$service"
        fi
        return 1
    fi
}

# Função para verificar Redis
check_redis() {
    echo -e "${YELLOW}🔄 Verificando status do Redis...${NC}"
    if redis-cli ping &>/dev/null; then
        echo -e "${GREEN}✅ Redis está respondendo${NC}"
        return 0
    else
        echo -e "${RED}❌ Redis não está respondendo${NC}"
        echo -e "${YELLOW}📊 Status do Redis:${NC}"
        brew services list | grep redis
        echo -e "${YELLOW}🔍 Últimas linhas do log:${NC}"
        tail -n 10 /usr/local/var/log/redis.log 2>/dev/null || echo "Log não encontrado"
        return 1
    fi
}

# Função para testar API
test_api() {
    echo -e "${YELLOW}🔍 Testando API...${NC}"
    
    # Test health endpoint
    response=$(curl -s http://localhost:8000/health)
    if [[ $response == *"healthy"* ]]; then
        echo -e "${GREEN}✅ Health check passou${NC}"
    else
        echo -e "${RED}❌ Health check falhou${NC}"
        return 1
    fi
    
    # Test docs
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs)
    if [[ $response == "200" ]]; then
        echo -e "${GREEN}✅ Documentação está acessível${NC}"
    else
        echo -e "${RED}❌ Documentação não está acessível${NC}"
        return 1
    fi
    
    return 0
}

# Iniciar serviços em background
echo -e "${YELLOW}🚀 Iniciando serviços...${NC}"

# Limpar logs antigos
rm -f logs/api.log logs/gui.log

# Iniciar API
echo -e "${YELLOW}📡 Iniciando API...${NC}"
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload > logs/api.log 2>&1 &
API_PID=$!

# Iniciar GUI
echo -e "${YELLOW}🖥️ Iniciando GUI...${NC}"
uvicorn src.web.main:app --host 0.0.0.0 --port 8080 --reload > logs/gui.log 2>&1 &
GUI_PID=$!

# Aguardar serviços iniciarem
echo -e "${YELLOW}⏳ Aguardando serviços iniciarem...${NC}"
sleep 5

# Verificar serviços
services_ok=true

# Verificar API
check_service 8000 "API" "logs/api.log" || services_ok=false

# Verificar GUI
check_service 8080 "GUI" "logs/gui.log" || services_ok=false

# Verificar Redis
check_redis || services_ok=false

if ! $services_ok; then
    echo -e """
${RED}❌ Alguns serviços falharam ao iniciar.${NC}

${YELLOW}🔍 Diagnóstico:${NC}
1. Verifique se as portas 8000 e 8080 não estão em uso:
   lsof -i :8000
   lsof -i :8080

2. Verifique se o Redis está instalado e rodando:
   brew services restart redis

3. Verifique os logs completos:
   API: cat logs/api.log
   GUI: cat logs/gui.log

4. Verifique as dependências:
   pip list | grep -E 'fastapi|uvicorn|redis'
"""
    
    # Matar processos
    echo -e "${YELLOW}🔄 Parando processos...${NC}"
    kill $API_PID $GUI_PID 2>/dev/null
    
    exit 1
fi

# Testar API
if test_api; then
    echo -e """
${GREEN}✅ Setup completo! Serviços disponíveis:${NC}
🔹 API: http://localhost:8000
🔹 API Docs: http://localhost:8000/docs
🔹 GUI: http://localhost:8080
🔹 Redis: localhost:6379

${YELLOW}Logs disponíveis em:${NC}
📝 API: tail -f logs/api.log
📝 GUI: tail -f logs/gui.log

${YELLOW}Para parar os serviços:${NC}
kill $API_PID $GUI_PID
"""
else
    echo -e "${RED}❌ Testes da API falharam${NC}"
    services_ok=false
fi

if ! $services_ok; then
    echo -e "${RED}Matando processos...${NC}"
    kill $API_PID $GUI_PID 2>/dev/null
    exit 1
fi

# Manter script rodando
wait 