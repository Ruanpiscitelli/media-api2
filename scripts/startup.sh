#!/bin/bash

# Download models if needed
/workspace/download_models.sh

# Iniciar Redis
service redis-server start

# Iniciar ComfyUI
cd /workspace/ComfyUI
nohup python main.py --listen 0.0.0.0 --port 8188 --enable-cors-header > /workspace/logs/comfyui.log 2>&1 &

# Iniciar API
cd /workspace/media-api2
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4 > /workspace/logs/api.log 2>&1 &

# Manter container rodando e monitorar logs
tail -f /workspace/logs/*.log 