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
   - Image: `runpod/stable-diffusion:web-ui-10.2.1-cuda11.7.1`

### 2. Docker Options
```
-p 8000:8000 -p 8188:8188 -p 6379:6379 -p 8080:8080 Docker Options: --gpus all
```

### 3. Environment Variables
```
NVIDIA_VISIBLE_DEVICES=all
DATA_DIRECTORY=/workspace
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
WORKERS=4
TIMEOUT=300
CORS_ORIGINS=*
ALLOWED_HOSTS=*
TRUSTED_HOSTS=*
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
COMFY_HOST=0.0.0.0
COMFY_PORT=8188
COMFY_WEBSOCKET_PORT=8188
MEDIA_DIR=/workspace/media
TEMP_DIR=/workspace/media/temp
LOG_DIR=/workspace/logs
MODELS_DIR=/workspace/models
CACHE_DIR=/workspace/cache
```

### 4. Onstart Script
```bash
#!/bin/bash
exec 3>&1 4>&2
trap 'exec 2>&4 1>&3' 0 1 2 3
exec 1>/tmp/setup.log 2>&1

apt-get update && apt-get install -y git python3-pip redis-server net-tools

mkdir -p /workspace/logs /workspace/media /workspace/cache /workspace/models /workspace/media/temp /workspace/models/lora /workspace/models/checkpoints

if [ ! -d "/workspace/media-api2" ]; then git clone https://github.com/seu-usuario/media-api2.git /workspace/media-api2; fi
if [ ! -d "/workspace/ComfyUI" ]; then git clone https://github.com/comfyanonymous/ComfyUI.git /workspace/ComfyUI; fi

python3 -m venv /workspace/venv
source /workspace/venv/bin/activate

pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install uvicorn fastapi redis python-jose[cryptography] python-multipart

cd /workspace/media-api2 && pip install -r requirements.txt
cd /workspace/ComfyUI && pip install -r requirements.txt

service redis-server start

cd /workspace/ComfyUI
nohup python main.py --listen 0.0.0.0 --port 8188 > /workspace/logs/comfyui.log 2>&1 &

sleep 10

cd /workspace/media-api2
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4 > /workspace/logs/api.log 2>&1 &

tail -f /workspace/logs/api.log /workspace/logs/comfyui.log /tmp/setup.log &

exec tail -f /dev/null
```

## 📊 Monitoramento

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

# ComfyUI logs
tail -f /workspace/logs/comfyui.log

# Setup logs
tail -f /tmp/setup.log

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

