# Media API

API avançada para geração de mídia com suporte a processamento distribuído em múltiplas GPUs.

## 🚀 Funcionalidades

### Síntese de Voz
- ✨ Geração de áudio com Fish Speech
- 📝 Suporte a textos longos com processamento em chunks
- 🔄 Streaming em tempo real
- 🎭 Múltiplas vozes e emoções
- 🎛️ Controle de velocidade, tom e volume
- 🎨 Efeitos de áudio (reverb, EQ, normalização)
- 👥 Clonagem de voz personalizada

### Otimização GPU
- ⚡ Processamento paralelo em múltiplas GPUs
- 📊 Balanceamento dinâmico de carga
- 🔄 Failover automático
- 📈 Monitoramento em tempo real

### API
- 🔐 Autenticação JWT
- 📝 Documentação Swagger
- ⚡ Rate limiting baseado em GPU/hora
- 🔄 Versionamento de endpoints
- 🎯 Webhooks para notificações

## 🛠️ Tecnologias

- FastAPI
- PyTorch
- CUDA
- Fish Speech
- Redis
- Prometheus/Grafana
- NLTK
- FFmpeg

## 📦 Instalação no Vast.ai

### 1. Configuração da Instância

1. Acesse [Vast.ai](https://vast.ai)
2. Selecione uma instância com:
   - GPU: RTX 4090 (1-4x)
   - RAM: 32GB+
   - Disk: 100GB+
   - Image: `nvidia/cuda:11.8.0-devel-ubuntu22.04`

### 2. Docker Options
```bash
-p 8000:8000 \    # API FastAPI
-p 8080:8080 \    # GUI Streamlit
-p 6379:6379 \    # Redis
-p 9090:9090 \    # Prometheus
-p 3000:3000 \    # Grafana
--gpus all
```

### 3. Environment Variables
Crie um arquivo `.env` com as seguintes variáveis:
```bash
# Sistema
NVIDIA_VISIBLE_DEVICES=all
DATA_DIRECTORY=/workspace
DEBUG=false

# API
API_HOST=0.0.0.0
API_PORT=8000
WORKERS=4
TIMEOUT=300
API_KEY=seu_api_key_aqui

# Segurança
CORS_ORIGINS=*
ALLOWED_HOSTS=*
TRUSTED_HOSTS=*

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Diretórios
MEDIA_DIR=/workspace/media
TEMP_DIR=/workspace/media/temp
LOG_DIR=/workspace/logs
MODELS_DIR=/workspace/models
CACHE_DIR=/workspace/cache
```

### 4. Execução

#### Método 1: Script de Setup
```bash
# Clone o repositório
git clone https://github.com/Ruanpiscitelli/media-api2.git
cd media-api2

# Execute o script de setup
chmod +x scripts/setup/entrypoint.sh
./scripts/setup/entrypoint.sh
```

#### Método 2: Docker
```bash
# Build da imagem
docker build -t media-api .

# Execução do container
docker run -d \
  --env-file .env \
  -p 8000:8000 \
  -p 8080:8080 \
  -p 6379:6379 \
  -p 9090:9090 \
  -p 3000:3000 \
  --gpus all \
  media-api
```

### 5. Verificação da Instalação

1. Verifique os serviços:
```bash
# API
curl http://localhost:8000/health

# Redis
redis-cli ping

# Prometheus
curl http://localhost:9090/-/healthy

# Grafana
curl http://localhost:3000/api/health
```

2. Acesse as interfaces:
- API Docs: http://localhost:8000/docs
- GUI: http://localhost:8080
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

3. Monitore os logs:
```bash
tail -f /workspace/logs/*.log
```

## 📄 Monitoramento

### Métricas Disponíveis
- `/metrics`: Métricas Prometheus
- `/health`: Status do sistema
- `/docs`: Documentação OpenAPI

### Dashboards Grafana
- GPU Utilization
- API Performance
- Error Rates
- Resource Usage

## 🔧 Manutenção

### Scripts Úteis
```bash
# Backup
./scripts/maintenance/backup.sh

# Limpeza
./scripts/maintenance/cleanup.sh

# Atualização
./scripts/maintenance/update.sh
```

### Logs
```bash
# API logs
tail -f /workspace/logs/api.log

# GPU logs
nvidia-smi -l 1
```

## 📝 Documentação

- API: `/docs` ou `/redoc`
- Swagger: `/openapi.json`
- Postman Collection: `docs/postman/collection.json`

## 🤝 Contribuição

1. Fork o projeto
2. Crie sua branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## Modelos

Os modelos não são incluídos no repositório devido ao tamanho. Para baixar:

```bash
# Execute o script de download
./scripts/download_models.sh
```
d
Ou baixe manualmente:
- SDXL Base: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
- SDXL Refiner: https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0
- SDXL VAE: https://huggingface.co/stabilityai/sdxl-vae

