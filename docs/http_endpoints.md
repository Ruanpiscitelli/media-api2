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
POST /v2/comfy/execute
```
Executa um workflow do ComfyUI.

**Request Body:**
```json
{
  "workflow": {
    // Workflow JSON do ComfyUI
  },
  "inputs": {
    // Inputs específicos para o workflow
  },
  "priority": 0 // Opcional, prioridade da execução (0-10)
}
```

**Response:**
```json
{
  "task_id": "uuid-v4",
  "status": "queued",
  "estimated_time": 120 // Tempo estimado em segundos
}
```

### List Workflows
```http
GET /v2/comfy/workflows
```
Lista todos os workflows disponíveis.

**Response:**
```json
{
  "workflows": [
    {
      "name": "workflow1",
      "description": "Descrição do workflow",
      "created_at": 1234567890
    }
  ]
}
```

### Save Workflow
```http
POST /v2/comfy/workflows/{name}
```
Salva um novo workflow.

**Path Parameters:**
- name: Nome do workflow

**Request Body:**
```json
{
  // Workflow JSON do ComfyUI
}
```

**Response:**
```json
{
  "status": "success"
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

### Status do Sistema
```http
GET /system/status
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "status": "online",
    "gpu_usage": {
        "gpu0": 45.5,
        "gpu1": 32.1
    },
    "queue_size": 5,
    "active_workers": 2,
    "uptime": 86400.5
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

### Métricas
```http
GET /system/metrics
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Logs do Sistema
```http
GET /system/logs
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Query Parameters:
  - service: string (all|api|comfyui|system) = "all"
  - limit: integer = 100
  - level: string (optional) = null
```

**Resposta (200 OK)**
```json
{
    "logs": [
        {
            "timestamp": "2024-01-30T12:00:00Z",
            "level": "INFO",
            "message": "Sistema iniciado com sucesso"
        }
    ]
}
```

### Status das Filas
```http
GET /system/queue/status
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "high_priority": 2,
    "normal": 5,
    "batch": 10,
    "total_tasks": 17
}
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

### Executar Workflow Detalhado
```http
POST /workflow/execute
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

## 📦 Gerenciamento de Modelos

### Upload de Modelo
```http
POST /models/upload
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: multipart/form-data

Parameters:
  - file: File
  - name: string (optional)
  - type: string
  - description: string (optional)
  - metadata: object (optional)
```

**Resposta (200 OK)**
```json
{
    "status": "success",
    "model": {
        "id": "model_123",
        "name": "Meu Modelo",
        "type": "sdxl",
        "description": "Descrição do modelo",
        "uploaded_by": "username",
        "created_at": "2024-01-30T12:00:00Z"
    }
}
```

### Remover Modelo
```http
DELETE /models/{model_id}
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "status": "success",
    "message": "Modelo removido com sucesso"
}
```

## 🖥️ Processamento

### Processamento de Texto
```http
POST /v2/processing/text
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

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

### Processamento de Imagem
```http
POST /v2/processing/image
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "operations": [
        {
            "type": "resize",
            "params": {
                "width": 800,
                "height": 600
            }
        }
    ],
    "output_format": "PNG"
}
```

**Resposta (200 OK)**
```json
{
    "status": "success",
    "url": "http://exemplo.com/processed/image.png",
    "metadata": {
        "width": 800,
        "height": 600,
        "format": "PNG"
    }
}
```

## 🔔 Webhooks (Endpoints Adicionais)

### Atualizar Webhook
```http
PUT /webhooks/{webhook_id}
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
    "url": "https://seu-site.com/webhook",
    "events": ["video.completed", "image.completed"],
    "secret": "seu_secret_key",
    "description": "Webhook para notificações"
}
```

**Resposta (200 OK)**
```json
{
    "status": "success",
    "webhook": {
        "id": "webhook_123",
        "url": "https://seu-site.com/webhook",
        "events": ["video.completed", "image.completed"],
        "description": "Webhook para notificações",
        "updated_at": "2024-01-30T12:00:00Z"
    }
}
```

### Histórico de Execuções do Webhook
```http
GET /webhooks/{webhook_id}/history
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Query Parameters:
  - limit: integer = 100
```

**Resposta (200 OK)**
```json
{
    "history": [
        {
            "id": "exec_123",
            "event": "video.completed",
            "status": "success",
            "timestamp": "2024-01-30T12:00:00Z",
            "response": {
                "status_code": 200,
                "duration_ms": 150
            }
        }
    ]
}
```

## System Management

### List Processes
```http
GET /v2/system/processes
```
Lista todos os processos em execução.

**Response:**
```json
{
  "processes": [
    {
      "pid": 1234,
      "name": "python",
      "command": "python script.py",
      "status": "running",
      "cpu_percent": 50.0,
      "memory_percent": 5.0,
      "gpu_id": 0,
      "gpu_memory_used": 1000,
      "uptime": 3600
    }
  ]
}
```

### Kill Process
```http
POST /v2/system/processes/{pid}/kill
```
Mata um processo específico.

**Path Parameters:**
- pid: ID do processo

**Response:**
```json
{
  "status": "success",
  "message": "Process 1234 killed"
}
```

### Restart Process
```http
POST /v2/system/processes/{pid}/restart
```
Reinicia um processo específico.

**Path Parameters:**
- pid: ID do processo

**Response:**
```json
{
  "status": "success",
  "message": "Process 1234 restarted",
  "new_pid": 1235
}
```