# Configuração Vast.ai

## 1. Seleção da Instância

1. Acesse vast.ai
2. Selecione uma instância com:
   - GPU: RTX 4090 (1-4x)
   - RAM: 32GB+
   - Disk: 100GB+
   - Image: `runpod/stable-diffusion:web-ui-10.2.1-cuda11.7.1`

## 2. Configuração da Instância

### Docker Options:
```bash
-p 8000:8000 -p 8188:8188 -p 6379:6379 --gpus all --ipc=host
```

### Environment Variables:
```env
NVIDIA_VISIBLE_DEVICES=all
PYTHONUNBUFFERED=1
WORKSPACE=/workspace
PYTHONPATH=/workspace/media-api2
CUDA_HOME=/usr/local/cuda
PATH=/usr/local/cuda/bin:$PATH
LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
```

### Onstart Command:
```bash
wget -O /workspace/startup.sh https://raw.githubusercontent.com/Ruanpiscitelli/media-api2/main/scripts/setup/vast_startup.sh && chmod +x /workspace/startup.sh && /workspace/startup.sh
```

## 3. Verificação da Instalação

1. Aguarde 3-5 minutos para a instalação completa
2. Verifique os logs:
   ```bash
   tail -f /workspace/logs/setup.log
   ```

3. Teste os endpoints:
   - API: http://seu-ip:8000/docs
   - ComfyUI: http://seu-ip:8188

## 4. Troubleshooting

Se encontrar erros:

1. Verifique os logs:
   ```bash
   tail -f /workspace/logs/api.log     # Logs da API
   tail -f /workspace/logs/comfyui.log # Logs do ComfyUI
   ```

2. Verifique o status dos serviços:
   ```bash
   ps aux | grep python
   nvidia-smi  # Verificar GPUs
   ```

3. Reinicie os serviços:
   ```bash
   pkill -f uvicorn
   pkill -f ComfyUI
   /workspace/startup.sh
   ``` 