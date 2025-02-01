# Endpoints HTTP - Referência Completa

## 🔍 Índice
- [Autenticação](#autenticação)
- [ComfyUI](#comfyui)
- [Geração de Imagem](#geração-de-imagem)
- [Geração de Vídeo](#geração-de-vídeo)
- [Síntese de Voz](#síntese-de-voz)
- [Sistema](#sistema)
- [📝 Processamento de Texto e OCR](#processamento-de-texto-e-ocr)
- [🎬 JSON2Video](#json2video)
- [🖼️ Thumbnails](#thumbnails)
- [📋 Templates](#templates)
- [🎥 Vídeo (Endpoints Adicionais)](#vídeo-endpoints-adicionais)
- [🔔 Webhooks](#webhooks)
- [🛠️ Utilidades](#utilidades)
- [📊 Sistema](#sistema)

## 🔑 Autenticação

### Login
```http
POST /v2/auth/login
Content-Type: application/json

{
    "username": "seu_usuario",
    "password": "sua_senha"
}
```

**Resposta (200 OK)**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "expires_in": 3600
}
```

### Renovar Token
```http
POST /v2/auth/refresh
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "expires_in": 3600
}
```

## 🎨 ComfyUI

### Executar Workflow
```http
POST /comfy/execute
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "workflow": {
        "nodes": [
            {
                "type": "SDXLLoader",
                "inputs": {
                    "prompt": "uma paisagem futurista",
                    "negative_prompt": "baixa qualidade"
                }
            }
        ]
    },
    "timeout": 300,
    "priority": 1,
    "gpu_preference": 0
}
```

**Resposta (200 OK)**
```json
{
    "prompt_id": "abc123",
    "status": "processing",
    "estimated_time": 30
}
```

### Executar Workflow por Arquivo
```http
POST /comfy/execute/file
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "workflow_name": "sdxl_base",
    "timeout": 300,
    "priority": 1,
    "gpu_preference": 0
}
```

**Resposta (200 OK)**
```json
{
    "prompt_id": "abc123",
    "status": "processing",
    "estimated_time": 30
}
```

### Obter Status do Workflow
```http
GET /comfy/status/{prompt_id}
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "status": "completed",
    "progress": 100,
    "outputs": {
        "images": ["http://exemplo.com/output/123.png"],
        "metadata": {}
    }
}
```

### Obter Histórico
```http
GET /comfy/history
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "executions": [
        {
            "prompt_id": "abc123",
            "status": "completed",
            "created_at": "2024-01-30T12:00:00Z",
            "completed_at": "2024-01-30T12:01:00Z",
            "outputs": {}
        }
    ]
}
```

### Obter Informações dos Nós
```http
GET /comfy/object_info
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "nodes": {
        "SDXLLoader": {
            "inputs": ["prompt", "negative_prompt"],
            "outputs": ["model", "clip", "vae"]
        }
    }
}
```

## 🖼️ Geração de Imagem

### Gerar Imagem
```http
POST /generate/image
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "prompt": "uma paisagem futurista",
    "negative_prompt": "baixa qualidade",
    "width": 1024,
    "height": 1024,
    "num_inference_steps": 30,
    "guidance_scale": 7.5
}
```

**Resposta (200 OK)**
```json
{
    "id": "img_123",
    "url": "http://exemplo.com/images/123.png",
    "metadata": {
        "prompt": "uma paisagem futurista",
        "width": 1024,
        "height": 1024
    }
}
```

### Listar Estilos
```http
GET /generate/image/styles
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "styles": [
        {
            "id": "futuristic",
            "name": "Futurista",
            "description": "Estilo futurista e sci-fi"
        }
    ]
}
```

## 🎥 Geração de Vídeo

### Gerar Vídeo
```http
POST /generate/video
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "prompt": "uma cidade futurista à noite",
    "num_frames": 30,
    "fps": 24,
    "motion_scale": 1.0,
    "width": 1024,
    "height": 576
}
```

**Resposta (200 OK)**
```json
{
    "id": "vid_123",
    "status": "processing",
    "estimated_time": 120,
    "progress_url": "/generate/video/status/vid_123"
}
```

### Status do Vídeo
```http
GET /generate/video/status/{video_id}
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "id": "vid_123",
    "status": "completed",
    "progress": 100,
    "url": "http://exemplo.com/videos/123.mp4",
    "preview_url": "http://exemplo.com/videos/123_preview.gif"
}
```

## 🗣️ Síntese de Voz

### Sintetizar Voz
```http
POST /synthesize/speech
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "text": "Olá, como você está?",
    "voice_id": "pt_br_female",
    "emotion": "happy",
    "speed": 1.0
}
```

**Resposta (200 OK)**
```json
{
    "id": "speech_123",
    "url": "http://exemplo.com/audio/123.mp3",
    "duration": 2.5,
    "text": "Olá, como você está?"
}
```

### Listar Vozes
```http
GET /synthesize/speech/voices
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "voices": [
        {
            "id": "pt_br_female",
            "name": "Ana",
            "language": "pt-BR",
            "gender": "female"
        }
    ]
}
```

## 🔧 Sistema

### Status dos Recursos
```http
GET /comfy/resources
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "gpus": [
        {
            "id": 0,
            "total_vram": 24.0,
            "used_vram": 8.5,
            "temperature": 65,
            "utilization": 45
        }
    ],
    "system": {
        "total_ram": 64.0,
        "used_ram": 32.5,
        "cpu_percent": 75
    },
    "allocations": 3
}
```

### Health Check
```http
GET /health
```

**Resposta (200 OK)**
```json
{
    "status": "healthy",
    "version": "2.0.0",
    "uptime": 86400
}
```

## ❌ Respostas de Erro

### Erro de Autenticação (401)
```json
{
    "detail": "Token inválido ou expirado",
    "type": "authentication_error"
}
```

### Rate Limit Excedido (429)
```json
{
    "detail": "Muitas requisições. Tente novamente em alguns segundos.",
    "type": "rate_limit_exceeded"
}
```

### Erro de Recursos (500)
```json
{
    "detail": "Erro ao executar workflow: VRAM insuficiente. Necessário: 8GB",
    "type": "resource_error"
}
```

### Timeout (408)
```json
{
    "detail": "Timeout ao executar workflow",
    "type": "timeout_error"
}
```

## 📝 Headers Comuns

### Request Headers
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json
Accept: application/json
```

### Response Headers
```http
Content-Type: application/json
X-RateLimit-Limit: 500
X-RateLimit-Remaining: 499
X-RateLimit-Reset: 1635789600
```

## 📝 Processamento de Texto e OCR

### Processar Texto
```http
POST /v2/processing/text
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "text": "Texto para processar",
    "font_name": "Arial",
    "size": 32,
    "max_width": 800,
    "language": "pt-br",
    "color": [0, 0, 0],
    "alignment": "left"
}
```

**Resposta (200 OK)**
```json
{
    "status": "success",
    "image": "base64_encoded_image",
    "metrics": {
        "width": 800,
        "height": 150,
        "lines": 3
    }
}
```

## 🎬 JSON2Video

### Criar Projeto de Vídeo
```http
POST /json2video/projects
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "scenes": [
        {
            "duration": 5,
            "elements": [
                {
                    "type": "text",
                    "content": "Título do Vídeo",
                    "position": {"x": 0.5, "y": 0.5},
                    "style": {
                        "fontSize": 48,
                        "color": "#FFFFFF"
                    }
                }
            ]
        }
    ],
    "audio": {
        "text": "Narração do vídeo",
        "voice_id": "pt_br_female"
    }
}
```

**Resposta (200 OK)**
```json
{
    "project_id": "proj_123",
    "status": "processing",
    "progress": 0,
    "estimated_time": 60
}
```

### Gerar Preview
```http
POST /json2video/preview
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "project_id": "proj_123",
    "scene_index": 0,
    "time": 2.5
}
```

**Resposta (200 OK)**
```json
{
    "preview_url": "http://exemplo.com/previews/123.jpg",
    "timestamp": 2.5
}
```

## 🖼️ Thumbnails

### Gerar Thumbnail
```http
POST /thumbnails/generate
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "video_url": "http://exemplo.com/video.mp4",
    "time": 5.0,
    "width": 640,
    "height": 360
}
```

**Resposta (200 OK)**
```json
{
    "thumbnail_url": "http://exemplo.com/thumbnails/123.jpg",
    "width": 640,
    "height": 360,
    "timestamp": 5.0
}
```

### Gerar Thumbnails em Lote
```http
POST /thumbnails/batch
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "videos": [
        {
            "url": "http://exemplo.com/video1.mp4",
            "time": 5.0
        },
        {
            "url": "http://exemplo.com/video2.mp4",
            "time": 10.0
        }
    ],
    "width": 640,
    "height": 360
}
```

**Resposta (200 OK)**
```json
{
    "thumbnails": [
        {
            "video_url": "http://exemplo.com/video1.mp4",
            "thumbnail_url": "http://exemplo.com/thumbnails/123.jpg",
            "timestamp": 5.0
        },
        {
            "video_url": "http://exemplo.com/video2.mp4",
            "thumbnail_url": "http://exemplo.com/thumbnails/124.jpg",
            "timestamp": 10.0
        }
    ]
}
```

## 📋 Templates

### Listar Templates
```http
GET /templates
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "templates": [
        {
            "id": "template_123",
            "name": "Template Básico",
            "description": "Template para vídeos simples",
            "preview_url": "http://exemplo.com/previews/template_123.jpg"
        }
    ]
}
```

### Obter Template
```http
GET /templates/{template_id}
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "id": "template_123",
    "name": "Template Básico",
    "description": "Template para vídeos simples",
    "config": {
        "scenes": [],
        "styles": {}
    }
}
```

### Gerar a partir de Template
```http
POST /templates/generate
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "template_id": "template_123",
    "variables": {
        "title": "Meu Vídeo",
        "subtitle": "Uma descrição legal"
    }
}
```

## 🎥 Vídeo (Endpoints Adicionais)

### Criar Slideshow
```http
POST /v2/video/slideshow
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "images": [
        "http://exemplo.com/imagem1.jpg",
        "http://exemplo.com/imagem2.jpg"
    ],
    "duration_per_image": 3,
    "transition": "fade",
    "music_url": "http://exemplo.com/musica.mp3"
}
```

### Adicionar Overlay
```http
POST /v2/video/overlay
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "video_url": "http://exemplo.com/video.mp4",
    "overlay_url": "http://exemplo.com/overlay.png",
    "position": {"x": 0.1, "y": 0.1},
    "size": {"width": 0.2, "height": 0.2},
    "start_time": 0,
    "end_time": 10
}
```

## 🔔 Webhooks

### Registrar Webhook
```http
POST /webhooks/register
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "url": "https://seu-site.com/webhook",
    "events": ["video.completed", "image.completed"],
    "secret": "seu_secret_key"
}
```

### Listar Webhooks
```http
GET /webhooks/list
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Histórico de Eventos
```http
GET /webhooks/{webhook_id}/history
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Testar Webhook
```http
POST /webhooks/{webhook_id}/test
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

## 🛠️ Utilidades

### Upload de Arquivo
```http
POST /utils/upload
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: multipart/form-data

file: <arquivo>
```

### Otimizar Mídia
```http
POST /utils/optimize
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "url": "http://exemplo.com/video.mp4",
    "type": "video",
    "quality": "high",
    "target_size": "10MB"
}
```

### Uso de Armazenamento
```http
GET /utils/storage/usage
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Listar Arquivos
```http
GET /utils/files
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Mover Arquivo
```http
POST /utils/files/move
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "source": "pasta1/arquivo.mp4",
    "destination": "pasta2/arquivo.mp4"
}
```

## 📊 Sistema

### Status do Sistema
```http
GET /system/status
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Métricas
```http
GET /system/metrics
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Status da Fila
```http
GET /system/queue
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Status das GPUs
```http
GET /system/gpu/status
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Logs do Sistema
```http
GET /system/logs
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Tarefas Ativas
```http
GET /system/tasks/active
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Cancelar Tarefa
```http
POST /system/tasks/{task_id}/cancel
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

## 🎮 GPU Management

### Alocar GPU
```http
POST /gpu/allocate
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "gpu_ids": [0, 1],
    "task_type": "render"
}
```

**Resposta (200 OK)**
```json
{
    "status": "allocated",
    "gpus": [
        {
            "id": 0,
            "vram_available": 8192,
            "utilization": 0
        },
        {
            "id": 1,
            "vram_available": 8192,
            "utilization": 0
        }
    ]
}
```

## 🔄 Workflow Management

### Listar Templates de Workflow
```http
GET /templates
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "templates": [
        {
            "id": "workflow_1",
            "name": "Processamento Básico",
            "description": "Pipeline básico de processamento",
            "parameters": ["input_image", "style"]
        }
    ]
}
```

### Executar Workflow
```http
POST /execute
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "workflow_id": "workflow_1",
    "parameters": {
        "input_image": "https://exemplo.com/imagem.jpg",
        "style": "artistic"
    },
    "resources": {
        "gpu_preference": 0
    }
}
```

**Resposta (200 OK)**
```json
{
    "status": "success",
    "result": {
        "output_url": "https://exemplo.com/resultado.jpg"
    },
    "execution_time": 5.2
}
```

## 🏥 Health Check Detalhado

### Status Completo do Sistema
```http
GET /health/full
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "database": {
        "status": "healthy",
        "latency_ms": 5
    },
    "redis": {
        "status": "healthy",
        "used_memory": "1.2GB"
    },
    "gpus": [
        {
            "id": 0,
            "status": "available",
            "vram": {
                "total": 24576,
                "used": 1024,
                "free": 23552
            },
            "temperature": 45
        }
    ],
    "services": {
        "comfyui": true,
        "cache": true
    }
}
```

## 🗣️ Síntese de Voz (Parâmetros Adicionais)

### Sintetizar Voz Avançado
```http
POST /synthesize/speech
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "text": "Texto para sintetizar",
    "voice_id": "pt_br_female",
    "emotion": "neutral",
    "speed": 1.0,
    "pitch": 0.0,
    "volume": 1.0
}
```

**Resposta (200 OK)**
```json
{
    "id": "speech_123",
    "url": "http://exemplo.com/audio/123.mp3",
    "duration": 2.5,
    "text": "Texto para sintetizar",
    "metadata": {
        "voice": "pt_br_female",
        "emotion": "neutral",
        "speed": 1.0,
        "pitch": 0.0,
        "volume": 1.0
    }
}
```

## 🔐 Autenticação (Endpoints Adicionais)

### Registrar Novo Usuário
```http
POST /v2/auth/register
Content-Type: application/json

{
    "username": "novo_usuario",
    "email": "usuario@exemplo.com",
    "password": "senha_segura",
    "plan": "free"
}
```

**Resposta (200 OK)**
```json
{
    "message": "Usuário registrado com sucesso",
    "user_id": "user_123"
}
```

### Atualizar Plano do Usuário
```http
PUT /v2/auth/me/plan
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "plan": "premium"
}
```

**Resposta (200 OK)**
```json
{
    "user_id": "user_123",
    "plan": "premium",
    "updated_at": "2024-01-30T12:00:00Z"
}
```

## 🖼️ Thumbnails (Parâmetros Adicionais)

### Gerar Thumbnail Avançado
```http
POST /thumbnails/generate
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "video_url": "http://exemplo.com/video.mp4",
    "width": 320,
    "height": 180,
    "timestamp": 5.0,
    "quality": 85,
    "format": "JPEG",
    "smart_crop": true
}
```

**Resposta (200 OK)**
```json
{
    "status": "success",
    "url": "http://exemplo.com/thumbnails/123.jpg",
    "metadata": {
        "width": 320,
        "height": 180,
        "format": "JPEG",
        "quality": 85,
        "timestamp": 5.0,
        "file_size": 15240
    }
}
```