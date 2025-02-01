# API de Geração de Vídeos (json2video)

## Visão Geral

A API json2video permite criar vídeos dinamicamente usando especificações JSON. Suporta múltiplos formatos e templates otimizados para diferentes plataformas de mídia social.

## Base URL
```
https://api.seudominio.com/v2/json2video
```

## Endpoints

### Criar Vídeo
```http
POST /create
Content-Type: application/json
Authorization: Bearer <seu_token>

{
    "scenes": [...],
    "audio": {...},
    "format": "mp4",
    "quality": "high"
}
```

#### Parâmetros
- `scenes` (array, obrigatório): Lista de cenas do vídeo
- `audio` (object, opcional): Configuração de áudio
- `format` (string, opcional): Formato do vídeo (mp4, webm)
- `quality` (string, opcional): Qualidade do vídeo (low, medium, high)

#### Resposta
```json
{
    "project_id": "abc123",
    "status": "processing",
    "progress": 0,
    "estimated_time": 120
}
```

### Verificar Status
```http
GET /status/{project_id}
Authorization: Bearer <seu_token>
```

#### Resposta
```json
{
    "project_id": "abc123",
    "status": "completed",
    "progress": 100,
    "video_url": "https://..."
}
```

### Gerar Preview
```http
POST /{project_id}/preview
Content-Type: application/json
Authorization: Bearer <seu_token>

{
    "scene_index": 0,
    "time": 5.0
}
```

#### Resposta
```json
{
    "preview_url": "https://...",
    "timestamp": 5.0
}
```

## Templates Disponíveis

### 1. YouTube Intro
Template para intros profissionais de vídeos do YouTube.

```http
POST /create
Content-Type: application/json

{
    "template": "youtube_intro",
    "params": {
        "channel_name": "Seu Canal",
        "logo_url": "https://...",
        "background_video": "https://...",
        "background_music": "https://..."
    }
}
```

**Características:**
- Duração: 10 segundos
- Resolução: 1920x1080
- FPS: 60
- Efeitos: Partículas, color grading
- Animações: Logo e texto

### 2. Instagram Story
Template para stories do Instagram com elementos interativos.

```http
POST /create
Content-Type: application/json

{
    "template": "instagram_story",
    "params": {
        "background_media": "https://...",
        "title": "Seu Título",
        "cta_text": "Swipe Up",
        "brand_logo": "https://..."
    }
}
```

**Características:**
- Duração: 15 segundos
- Resolução: 1080x1920
- FPS: 30
- Elementos: CTA, logo, título
- Efeitos: Gradientes, animações

### 3. YouTube Shorts
Template para vídeos curtos do YouTube.

```http
POST /create
Content-Type: application/json

{
    "template": "youtube_shorts",
    "params": {
        "video_url": "https://...",
        "captions": [
            {"text": "Primeira legenda", "time": 0},
            {"text": "Segunda legenda", "time": 5}
        ],
        "background_music": "https://..."
    }
}
```

**Características:**
- Duração: 60 segundos
- Resolução: 1080x1920
- FPS: 60
- Legendas automáticas
- Elementos de engajamento

### 4. TikTok Tutorial
Template para tutoriais em formato TikTok.

```http
POST /create
Content-Type: application/json

{
    "template": "tiktok_tutorial",
    "params": {
        "steps": [
            {
                "title": "Passo 1",
                "video": "https://...",
                "description": "Primeiro passo do tutorial"
            }
        ],
        "background_music": "https://...",
        "creator_info": {
            "username": "@seuperfil",
            "avatar": "https://..."
        }
    }
}
```

**Características:**
- Duração: 60 segundos
- Resolução: 1080x1920
- FPS: 60
- Passos numerados
- Barra de progresso
- Perfil do criador

## Estrutura de Cenas

Cada cena pode conter os seguintes elementos:

```json
{
    "duration": 5.0,
    "elements": [
        {
            "type": "text",
            "content": "Seu texto",
            "position": {"x": 0.5, "y": 0.5},
            "style": {
                "fontSize": 32,
                "color": "#FFFFFF",
                "fontFamily": "Roboto-Bold"
            }
        },
        {
            "type": "image",
            "content": "https://...",
            "position": {"x": 0.5, "y": 0.5},
            "style": {
                "size": {"width": 500, "height": 300}
            }
        },
        {
            "type": "video",
            "content": "https://...",
            "position": {"x": 0.5, "y": 0.5},
            "style": {
                "size": {"width": 1080, "height": 1920}
            }
        }
    ],
    "transition": {
        "type": "fade",
        "duration": 0.5
    }
}
```

## Configurações de Áudio

```json
{
    "audio": {
        "narration": {
            "text": "Texto para narração",
            "voice_id": "voz-1",
            "volume": 1.0
        },
        "music": {
            "url": "https://...",
            "volume": 0.3,
            "fade": {
                "in": 2.0,
                "out": 2.0
            }
        }
    }
}
```

## Efeitos Disponíveis

### Visuais
- `fade`: Transição suave
- `slide`: Deslizamento
- `zoom`: Aproximação/afastamento
- `blur`: Desfoque
- `gradient`: Sobreposição gradiente
- `particles`: Efeitos de partículas

### Animações
- `scale`: Escala
- `bounce`: Quique
- `typewriter`: Digitação
- `pulse`: Pulsação
- `float`: Flutuação

### Áudio
- `fade`: Fade in/out
- `ducking`: Redução automática do volume da música durante narração
- `transition`: Efeitos sonoros de transição

## Limites e Restrições

- Duração máxima: 300 segundos
- Tamanho máximo de arquivo: 500MB
- Formatos suportados:
  - Vídeo: MP4, WebM
  - Áudio: MP3, WAV
  - Imagem: JPG, PNG, WebP
- Rate Limits:
  - 100 requisições/hora para planos gratuitos
  - 1000 requisições/hora para planos premium

## Códigos de Erro

- `400`: Parâmetros inválidos
- `401`: Não autorizado
- `403`: Limite excedido
- `404`: Projeto não encontrado
- `500`: Erro interno do servidor

## Exemplos

### 1. Slideshow Básico
```json
{
    "scenes": [
        {
            "duration": 5.0,
            "elements": [
                {
                    "type": "image",
                    "content": "https://...",
                    "position": {"x": 0.5, "y": 0.5}
                }
            ],
            "transition": {"type": "fade", "duration": 1.0}
        }
    ],
    "audio": {
        "music": {
            "url": "https://...",
            "volume": 0.3
        }
    }
}
```

### 2. Vídeo com Overlay
```json
{
    "scenes": [
        {
            "duration": 30.0,
            "elements": [
                {
                    "type": "video",
                    "content": "https://...",
                    "position": {"x": 0.5, "y": 0.5}
                },
                {
                    "type": "text",
                    "content": "Seu texto",
                    "position": {"x": 0.5, "y": 0.9},
                    "style": {
                        "fontSize": 32,
                        "color": "#FFFFFF"
                    }
                }
            ]
        }
    ]
}
```

## Boas Práticas

1. **Otimização de Assets**
   - Comprima imagens e vídeos antes do upload
   - Use formatos apropriados para cada tipo de mídia
   - Mantenha as dimensões dentro dos limites recomendados

2. **Performance**
   - Pré-carregue assets pesados
   - Use caching quando possível
   - Monitore o progresso de geração

3. **Qualidade**
   - Teste diferentes configurações de qualidade
   - Verifique a sincronização de áudio
   - Valide as animações e transições

4. **Responsividade**
   - Use posições relativas (0.0 a 1.0)
   - Adapte fontes para diferentes resoluções
   - Considere diferentes proporções de tela 