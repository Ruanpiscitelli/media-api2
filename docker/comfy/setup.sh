#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Função para imprimir mensagens
print_message() {
    echo -e "${GREEN}[ComfyUI Setup]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[Aviso]${NC} $1"
}

print_error() {
    echo -e "${RED}[Erro]${NC} $1"
}

# Verificar se o Docker está instalado
if ! command -v docker &> /dev/null; then
    print_error "Docker não encontrado. Por favor, instale o Docker primeiro."
    exit 1
fi

# Verificar se o docker-compose está instalado
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose não encontrado. Por favor, instale o docker-compose primeiro."
    exit 1
fi

# Verificar se o NVIDIA Container Toolkit está instalado
if ! command -v nvidia-smi &> /dev/null; then
    print_error "NVIDIA Container Toolkit não encontrado. Por favor, instale-o primeiro."
    exit 1
fi

# Criar diretórios necessários
print_message "Criando diretórios..."
mkdir -p ../models/{stable-diffusion,lora,vae,embeddings}
mkdir -p ../outputs
mkdir -p ../logs

# Verificar se há modelos SDXL base
if [ -z "$(ls -A ../models/stable-diffusion)" ]; then
    print_warning "Nenhum modelo SDXL base encontrado."
    print_warning "Por favor, baixe pelo menos um modelo SDXL base e coloque em ../models/stable-diffusion"
fi

# Criar arquivo .env se não existir
if [ ! -f ../.env ]; then
    print_message "Criando arquivo .env..."
    echo "COMFYUI_API_KEY=$(openssl rand -hex 32)" > ../.env
fi

# Criar arquivo .htpasswd para autenticação das métricas
if [ ! -f nginx/.htpasswd ]; then
    print_message "Criando credenciais para métricas..."
    read -p "Digite o usuário para acesso às métricas: " metrics_user
    docker run --rm httpd:2.4-alpine htpasswd -Bbn $metrics_user $(openssl rand -hex 16) > nginx/.htpasswd
fi

# Construir e iniciar os containers
print_message "Construindo e iniciando os containers..."
docker-compose -f docker-compose.yml build
docker-compose -f docker-compose.yml up -d

# Verificar se os containers estão rodando
if [ $(docker ps -q -f name=comfyui) ] && [ $(docker ps -q -f name=comfy-nginx) ]; then
    print_message "ComfyUI está rodando!"
    print_message "Acesse: http://localhost"
    print_message "Métricas: http://localhost/metrics"
else
    print_error "Erro ao iniciar os containers. Verifique os logs:"
    docker-compose -f docker-compose.yml logs
fi 