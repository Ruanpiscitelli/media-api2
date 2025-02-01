# API de Geração de YouTube Shorts

Esta documentação descreve os endpoints disponíveis para geração automática de YouTube Shorts usando IA.

## Autenticação

Todos os endpoints requerem autenticação via token JWT no header:

```http
Authorization: Bearer <seu_token>
```

## Endpoints

### 1. Geração de Short Original

#### POST /v2/shorts/generate

Gera um YouTube Short do zero usando IA, integrando geração de vídeo, música e voz.

**Request:**
```json
{
    "title": "Como fazer um bolo de chocolate",
    "description": "Receita fácil e rápida de bolo de chocolate caseiro",
    "duration": 60,
    "style": "cinematic",
    "music_prompt": "Uma música alegre e relaxante com piano",
    "voice_id": "pt_br_female_1",
    "hashtags": ["#receita", "#bolo", "#chocolate"],
    "watermark": "@chef_maria",
    "options": {
        "transitions": "fade",
        "color_grading": {
            "contrast": 1.2,
            "saturation": 1.1
        }
    }
}
```

**Response (200):**
```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "estimated_time": 240,
    "preview_url": "/media/shorts/preview_550e8400.gif"
}
```

### 2. Geração de Shorts a partir de Vídeo do YouTube

#### POST /v2/shorts/from-video

Analisa um vídeo do YouTube e gera múltiplos shorts a partir dos momentos mais interessantes.

**Request:**
```json
{
    "video_url": "https://www.youtube.com/watch?v=exemplo",
    "duration": 60,
    "num_shorts": 3,
    "style": "cinematic",
    "music_prompt": "Uma música energética",
    "voice_id": "pt_br_female_1",
    "hashtags": ["#exemplo", "#video"],
    "watermark": "@seu_canal",
    "options": {
        "min_segment_duration": 15,
        "max_segments": 5,
        "detection": {
            "faces": true,
            "motion": true,
            "audio_peaks": true
        }
    }
}
```

**Response (200):**
```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "estimated_time": 600,
    "preview_url": "/media/shorts/preview_550e8400.gif"
}
```

### 3. Geração de Shorts a partir de Upload

#### POST /v2/shorts/from-upload

Analisa um vídeo enviado e gera múltiplos shorts a partir dos momentos mais interessantes.

**Request:**
- Método: POST
- Content-Type: multipart/form-data
- Parâmetros do formulário:
  - `file`: Arquivo de vídeo (mp4, mov, avi)
  - `duration`: Duração máxima de cada short (15-60 segundos)
  - `num_shorts`: Número de shorts a gerar (1-10)
  - `style`: Estilo visual (cinematic, vlog, gaming)
  - `music_prompt`: Prompt para música (opcional)
  - `voice_id`: ID da voz para narração (opcional)
  - `hashtags`: JSON string com lista de hashtags (opcional)
  - `watermark`: Texto da marca d'água (opcional)
  - `options`: JSON string com opções avançadas (opcional)

**Response (200):**
```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "estimated_time": 600,
    "preview_url": "/media/shorts/preview_550e8400.gif"
}
```

### 4. Status da Geração

#### GET /v2/shorts/status/{task_id}

Verifica o status de uma tarefa de geração.

**Response (200):**
```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "progress": 100,
    "result": {
        "shorts": [
            {
                "video_url": "/media/shorts/short_550e8400_0.mp4",
                "preview_url": "/media/shorts/preview_550e8400_0.gif",
                "duration": 45,
                "segment": {
                    "start": 120.5,
                    "end": 165.5,
                    "duration": 45
                }
            },
            {
                "video_url": "/media/shorts/short_550e8400_1.mp4",
                "preview_url": "/media/shorts/preview_550e8400_1.gif",
                "duration": 30,
                "segment": {
                    "start": 245.0,
                    "end": 275.0,
                    "duration": 30
                }
            }
        ],
        "source_video": "/media/uploads/source_550e8400.mp4",
        "num_shorts": 2
    }
}
```

### 5. Upload de Vídeo Base

#### POST /v2/shorts/upload

Faz upload de um vídeo para usar como base do short.

**Request:**
- Método: POST
- Content-Type: multipart/form-data
- Corpo: arquivo de vídeo (mp4, mov, avi)

**Response (200):**
```json
{
    "status": "success",
    "video_path": "/media/uploads/shorts/video_550e8400.mp4"
}
```

### 6. Listagem de Templates

#### GET /v2/shorts/templates

Lista templates disponíveis para shorts.

**Response (200):**
```json
{
    "templates": [
        {
            "name": "Default Short",
            "description": "Template padrão para shorts",
            "version": "1.0",
            "preview": "/media/previews/default_short.jpg",
            "scenes": [
                {
                    "duration": "video_duration",
                    "elements": [
                        {
                            "type": "video",
                            "position": {"x": 0.5, "y": 0.5},
                            "style": {
                                "size": {
                                    "width": 1080,
                                    "height": 1920
                                },
                                "zoom": {
                                    "enabled": true,
                                    "scale": 1.1,
                                    "duration": "video_duration"
                                }
                            }
                        }
                    ]
                }
            ]
        }
    ]
}
```

## Funcionalidades

### Análise Automática de Vídeos

O sistema analisa automaticamente os vídeos para encontrar os momentos mais interessantes usando:

1. **Detecção de Movimento**
   - Análise frame a frame para identificar cenas com mais ação
   - Pontuação baseada na quantidade e intensidade do movimento

2. **Análise de Composição**
   - Avaliação de brilho e contraste
   - Detecção de faces e objetos importantes
   - Identificação de momentos visualmente impactantes

3. **Processamento de Áudio**
   - Detecção de picos de volume
   - Identificação de música e fala
   - Sincronização de cortes com batidas musicais

### Geração de Música e Voz

1. **Música de Fundo**
   - Geração de música original com Suno AI
   - Controle de estilo e energia
   - Sincronização automática com o vídeo

2. **Narração**
   - Vozes em português e inglês
   - Controle de emoção e estilo
   - Mixagem automática com música

### Templates e Efeitos

1. **Estilos Visuais**
   - Cinematográfico
   - Vlog
   - Gaming
   - Cada estilo com parâmetros específicos de cor e movimento

2. **Elementos Visuais**
   - Títulos animados
   - Hashtags
   - Marca d'água
   - Transições personalizadas

3. **Efeitos de Vídeo**
   - Zoom suave
   - Color grading
   - Motion blur
   - Estabilização

## Exemplos de Uso

### Python com aiohttp

```python
import aiohttp
import json
import asyncio

async def generate_shorts_from_youtube():
    async with aiohttp.ClientSession() as session:
        # Configurar request
        headers = {
            "Authorization": "Bearer seu_token",
            "Content-Type": "application/json"
        }
        
        data = {
            "video_url": "https://www.youtube.com/watch?v=exemplo",
            "duration": 60,
            "num_shorts": 3,
            "style": "cinematic",
            "music_prompt": "Uma música energética",
            "voice_id": "pt_br_female_1",
            "hashtags": ["#exemplo", "#video"],
            "watermark": "@seu_canal"
        }
        
        # Iniciar geração
        async with session.post(
            "http://api.exemplo.com/v2/shorts/from-video",
            headers=headers,
            json=data
        ) as response:
            result = await response.json()
            task_id = result["task_id"]
            
        # Aguardar conclusão
        while True:
            async with session.get(
                f"http://api.exemplo.com/v2/shorts/status/{task_id}",
                headers=headers
            ) as response:
                status = await response.json()
                if status["status"] == "completed":
                    print("Shorts gerados:")
                    for short in status["result"]["shorts"]:
                        print(f"- {short['video_url']}")
                    break
                elif status["status"] == "failed":
                    print(f"Erro: {status['error']}")
                    break
                print(f"Progresso: {status['progress']}%")
                await asyncio.sleep(5)

asyncio.run(generate_shorts_from_youtube())
```

### cURL

```bash
# Gerar shorts a partir de vídeo do YouTube
curl -X POST "http://api.exemplo.com/v2/shorts/from-video" \
  -H "Authorization: Bearer seu_token" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://www.youtube.com/watch?v=exemplo",
    "duration": 60,
    "num_shorts": 3,
    "style": "cinematic",
    "music_prompt": "Uma música energética",
    "voice_id": "pt_br_female_1",
    "hashtags": ["#exemplo", "#video"],
    "watermark": "@seu_canal"
  }'

# Upload de vídeo e geração de shorts
curl -X POST "http://api.exemplo.com/v2/shorts/from-upload" \
  -H "Authorization: Bearer seu_token" \
  -F "file=@video.mp4" \
  -F "duration=60" \
  -F "num_shorts=3" \
  -F "style=cinematic" \
  -F "music_prompt=Uma música energética" \
  -F "voice_id=pt_br_female_1" \
  -F 'hashtags=["#exemplo", "#video"]' \
  -F "watermark=@seu_canal"

# Verificar status
curl "http://api.exemplo.com/v2/shorts/status/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer seu_token"

# Listar templates
curl "http://api.exemplo.com/v2/shorts/templates" \
  -H "Authorization: Bearer seu_token"
```

## Códigos de Erro

- `400 Bad Request`: Parâmetros inválidos ou faltando
  - Vídeo muito curto ou longo
  - Formato de arquivo não suportado
  - Parâmetros inválidos

- `401 Unauthorized`: Token inválido ou expirado
  - Token ausente
  - Token expirado
  - Token inválido

- `403 Forbidden`: Sem permissão para o recurso
  - Limite de requisições excedido
  - Plano não permite a funcionalidade
  - IP bloqueado

- `404 Not Found`: Recurso não encontrado
  - Tarefa não encontrada
  - Template não encontrado
  - Vídeo não encontrado

- `429 Too Many Requests`: Limite de requisições excedido
  - Muitas requisições por minuto
  - Muitas tarefas simultâneas
  - Quota diária excedida

- `500 Internal Server Error`: Erro interno do servidor
  - Erro no processamento do vídeo
  - Erro na geração de música/voz
  - Erro no armazenamento

## Limites e Quotas

- **Requisições**
  - 50 requisições por hora por usuário
  - 5 tarefas simultâneas por usuário
  - 1000 requisições por dia por usuário

- **Vídeos**
  - Duração máxima do vídeo fonte: 60 minutos
  - Duração máxima de cada short: 60 segundos
  - Máximo de 10 shorts por vídeo
  - Tamanho máximo de upload: 500MB

- **Armazenamento**
  - Arquivos gerados são mantidos por 24 horas
  - Máximo de 10GB de armazenamento por usuário
  - Cache de templates por 1 hora

- **Processamento**
  - Timeout de processamento: 30 minutos
  - Uso máximo de GPU: 12GB VRAM
  - Prioridade baseada no plano do usuário