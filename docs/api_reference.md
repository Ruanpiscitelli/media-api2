# API de Geração de Mídia - Documentação

## 🚀 Introdução

Esta API fornece serviços de geração de mídia usando modelos de IA, incluindo geração de imagens com SDXL, vídeos com FastHunyuan e áudio com Fish Speech.

## 📝 Índice

1. [Autenticação](#autenticação)
2. [Rate Limiting](#rate-limiting)
3. [Endpoints](#endpoints)
   - [ComfyUI](#comfyui)
   - [Geração de Imagem](#geração-de-imagem)
   - [Geração de Vídeo](#geração-de-vídeo)
   - [Síntese de Voz](#síntese-de-voz)
4. [Recursos e Monitoramento](#recursos-e-monitoramento)
5. [Exemplos](#exemplos)
6. [Erros Comuns](#erros-comuns)

## 🔑 Autenticação

A API usa autenticação JWT. Para obter um token:

```http
POST /v2/auth/login
Content-Type: application/json

{
    "username": "seu_usuario",
    "password": "sua_senha"
}
```

Resposta:
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "expires_in": 3600
}
```

Use o token em todas as requisições subsequentes no header:
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

## ⚡ Rate Limiting

A API implementa os seguintes limites de requisições:

- Global: 500 requisições/segundo
- `/comfy/execute`: 50 req/s
- `/generate/image`: 100 req/s
- `/generate/video`: 20 req/s

Quando o limite é excedido, a API retorna:
```json
{
    "detail": "Muitas requisições. Tente novamente em alguns segundos.",
    "type": "rate_limit_exceeded"
}
```

## 🛠️ Endpoints

### ComfyUI

#### Executar Workflow
```http
POST /comfy/execute
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

#### Executar Workflow por Arquivo
```http
POST /comfy/execute/file
Content-Type: application/json

{
    "workflow_name": "sdxl_base",
    "timeout": 300,
    "priority": 1,
    "gpu_preference": 0
}
```

#### Obter Status
```http
GET /comfy/status/{prompt_id}
```

#### Obter Histórico
```http
GET /comfy/history
```

### Geração de Imagem

#### Gerar Imagem
```http
POST /generate/image
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

### Geração de Vídeo

#### Gerar Vídeo
```http
POST /generate/video
Content-Type: application/json

{
    "prompt": "uma cidade futurista à noite",
    "num_frames": 30,
    "fps": 24,
    "motion_scale": 1.0
}
```

### Síntese de Voz

#### Sintetizar Voz
```http
POST /synthesize/speech
Content-Type: application/json

{
    "text": "Olá, como você está?",
    "voice_id": "pt_br_female",
    "emotion": "happy",
    "speed": 1.0
}
```

## 📊 Recursos e Monitoramento

### Status dos Recursos
```http
GET /comfy/resources
```

Resposta:
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

## 📝 Exemplos

### Python com requests
```python
import requests

# Autenticação
response = requests.post(
    "http://api.exemplo.com/v2/auth/login",
    json={
        "username": "usuario",
        "password": "senha"
    }
)
token = response.json()["access_token"]

# Headers para todas as requisições
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Gerar imagem
response = requests.post(
    "http://api.exemplo.com/generate/image",
    headers=headers,
    json={
        "prompt": "uma paisagem futurista",
        "width": 1024,
        "height": 1024
    }
)

print(response.json())
```

### cURL
```bash
# Autenticação
curl -X POST "http://api.exemplo.com/v2/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username":"usuario","password":"senha"}'

# Gerar imagem
curl -X POST "http://api.exemplo.com/generate/image" \
     -H "Authorization: Bearer SEU_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
         "prompt": "uma paisagem futurista",
         "width": 1024,
         "height": 1024
     }'
```

## ❌ Erros Comuns

| Código | Descrição | Solução |
|--------|-----------|---------|
| 401 | Não autorizado | Verifique se o token é válido |
| 429 | Rate limit excedido | Aguarde alguns segundos |
| 500 | Erro interno | Contate o suporte |
| 408 | Timeout | Aumente o timeout ou simplifique o workflow |

### Exemplo de Erro
```json
{
    "detail": "Erro ao executar workflow: VRAM insuficiente. Necessário: 8GB",
    "type": "resource_error"
}
```

## 🔧 Configurações Recomendadas

- Timeout mínimo: 30 segundos
- Timeout máximo: 300 segundos
- Batch size máximo: 4
- VRAM mínima recomendada: 8GB
- RAM mínima recomendada: 16GB

## 📚 Recursos Adicionais

- [Documentação OpenAPI](/docs)
- [Exemplos de Workflows](/workflows)
- [Guia de Otimização](/docs/optimization.md)
- [FAQ](/docs/faq.md)

## 🆘 Suporte

Para suporte, entre em contato:
- Email: suporte@exemplo.com
- Discord: https://discord.gg/exemplo
- GitHub Issues: https://github.com/exemplo/issues 