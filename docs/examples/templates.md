# Exemplos de Uso - Sistema de Templates

Este documento demonstra como usar o sistema de templates para geração automática de imagens, similar ao Bannerbear e Creatomate.

## Criar um Template

```python
import requests
import json

# Configuração
api_url = "http://localhost:8000"
headers = {
    "Authorization": f"Bearer {seu_token}",
    "Content-Type": "application/json"
}

# Criar template para post de Instagram
template = {
    "name": "Post Instagram",
    "description": "Template para posts do Instagram",
    "width": 1080,
    "height": 1080,
    "category": "social_media",
    "tags": ["instagram", "social", "square"],
    "layers": [
        {
            "name": "background",
            "type": "image",
            "position": [0, 0],
            "dimensions": [1080, 1080],
            "default_image": "https://example.com/background.jpg"
        },
        {
            "name": "title",
            "type": "text",
            "position": [50, 50],
            "font": "Roboto-Bold",
            "size": 72,
            "color": [255, 255, 255],
            "default_text": "Título Principal"
        },
        {
            "name": "description",
            "type": "text",
            "position": [50, 200],
            "font": "Roboto-Regular",
            "size": 36,
            "color": [255, 255, 255],
            "default_text": "Descrição do post"
        },
        {
            "name": "logo",
            "type": "image",
            "position": [50, 900],
            "dimensions": [200, 100],
            "default_image": "https://example.com/logo.png"
        }
    ]
}

# Criar template
response = requests.post(
    f"{api_url}/v2/templates",
    headers=headers,
    json=template
)

if response.status_code == 200:
    result = response.json()
    template_id = result["template_id"]
    print(f"Template criado com ID: {template_id}")
```

## Gerar Imagem a partir do Template

```python
# Definir modificações
modifications = {
    "template_id": template_id,
    "modifications": [
        {
            "name": "background",
            "type": "image",
            "image_url": "https://example.com/nova_imagem.jpg"
        },
        {
            "name": "title",
            "type": "text",
            "text": "Promoção Especial!",
            "color": [255, 0, 0]  # Vermelho
        },
        {
            "name": "description",
            "type": "text",
            "text": "Aproveite nossos descontos exclusivos",
            "size": 42  # Aumentar tamanho
        }
    ],
    "output_format": "png",
    "quality": 90,
    "webhook_url": "https://seu-site.com/webhook"
}

# Gerar imagem
response = requests.post(
    f"{api_url}/v2/templates/generate",
    headers=headers,
    json=modifications
)

if response.status_code == 200:
    result = response.json()
    image_url = result["url"]
    print(f"Imagem gerada: {image_url}")
```

## Exemplos de Templates Comuns

### 1. Banner para Site

```python
banner_template = {
    "name": "Banner Site",
    "width": 1200,
    "height": 630,
    "category": "web",
    "layers": [
        {
            "name": "background",
            "type": "image",
            "position": [0, 0],
            "dimensions": [1200, 630]
        },
        {
            "name": "overlay",
            "type": "shape",
            "shape": "rectangle",
            "position": [0, 0],
            "dimensions": [1200, 630],
            "color": [0, 0, 0],
            "opacity": 0.5
        },
        {
            "name": "title",
            "type": "text",
            "position": [100, 200],
            "font": "Montserrat-Bold",
            "size": 64
        },
        {
            "name": "cta",
            "type": "text",
            "position": [100, 400],
            "font": "Montserrat-SemiBold",
            "size": 36
        }
    ]
}
```

### 2. Story do Instagram

```python
story_template = {
    "name": "Instagram Story",
    "width": 1080,
    "height": 1920,
    "category": "social_media",
    "layers": [
        {
            "name": "background",
            "type": "image",
            "position": [0, 0],
            "dimensions": [1080, 1920]
        },
        {
            "name": "gradient",
            "type": "shape",
            "shape": "gradient",
            "position": [0, 960],
            "dimensions": [1080, 960],
            "gradient": {
                "type": "linear",
                "start": [0, 0, 0, 0],
                "end": [0, 0, 0, 1]
            }
        },
        {
            "name": "title",
            "type": "text",
            "position": [50, 1200],
            "font": "Inter-Bold",
            "size": 72
        },
        {
            "name": "swipe_up",
            "type": "text",
            "position": [50, 1800],
            "font": "Inter-Regular",
            "size": 36,
            "default_text": "Deslize para cima ↑"
        }
    ]
}
```

### 3. Thumbnail para YouTube

```python
youtube_template = {
    "name": "YouTube Thumbnail",
    "width": 1280,
    "height": 720,
    "category": "video",
    "layers": [
        {
            "name": "background",
            "type": "image",
            "position": [0, 0],
            "dimensions": [1280, 720]
        },
        {
            "name": "title_background",
            "type": "shape",
            "shape": "rectangle",
            "position": [20, 500],
            "dimensions": [1240, 200],
            "color": [255, 0, 0],
            "opacity": 0.9
        },
        {
            "name": "title",
            "type": "text",
            "position": [40, 540],
            "font": "Roboto-Black",
            "size": 72,
            "color": [255, 255, 255]
        }
    ]
}
```

## Recursos Avançados

### 1. Animações e Efeitos

```python
modifications = {
    "template_id": template_id,
    "modifications": [
        {
            "name": "title",
            "type": "text",
            "text": "Texto Animado",
            "animation": {
                "type": "fade_in",
                "duration": 1.0,
                "delay": 0.5
            }
        },
        {
            "name": "background",
            "type": "image",
            "image_url": "https://example.com/imagem.jpg",
            "effects": [
                {
                    "type": "blur",
                    "radius": 5.0
                },
                {
                    "type": "brightness",
                    "value": 1.2
                }
            ]
        }
    ]
}
```

### 2. Condicionais

```python
modifications = {
    "template_id": template_id,
    "modifications": [
        {
            "name": "price_tag",
            "type": "text",
            "text": "R$ 99,90",
            "conditions": [
                {
                    "if": "price > 100",
                    "color": [255, 0, 0],
                    "badge": "expensive"
                },
                {
                    "if": "price < 50",
                    "color": [0, 255, 0],
                    "badge": "cheap"
                }
            ]
        }
    ]
}
```

### 3. Variáveis Dinâmicas

```python
modifications = {
    "template_id": template_id,
    "modifications": [
        {
            "name": "product_info",
            "type": "text",
            "text": "{{product_name}}\nR$ {{price}}",
            "variables": {
                "product_name": "Produto Especial",
                "price": "199,90"
            }
        }
    ]
}
```

## Webhooks

O sistema suporta webhooks para notificar quando a geração é concluída:

```python
{
    "event": "generation_completed",
    "template_id": "template_123",
    "output": {
        "url": "https://api.example.com/images/123.png",
        "format": "png",
        "width": 1080,
        "height": 1080,
        "size": 245678
    },
    "metadata": {
        "duration": 1.23,
        "timestamp": "2024-01-30T12:34:56Z"
    }
}
```

## Limites e Restrições

1. **Tamanhos Máximos**:
   - Imagem: 3840x2160px
   - Arquivo: 15MB
   - Template: 50 layers

2. **Formatos Suportados**:
   - Entrada: JPG, PNG, WebP
   - Saída: JPG, PNG, WebP, GIF

3. **Rate Limits**:
   - 100 gerações/minuto (plano básico)
   - 1000 gerações/minuto (plano pro)

4. **Fontes**:
   - 100+ fontes incluídas
   - Suporte a fontes personalizadas 