# Exemplos de Uso - Processamento de Imagem e Texto

Este documento demonstra como usar os endpoints de processamento de imagem e texto da API.

## Processamento de Texto

### Renderizar Texto com Fonte Personalizada

```python
import requests
import json

# Configuração
api_url = "http://localhost:8000"
headers = {
    "Authorization": f"Bearer {seu_token}",
    "Content-Type": "application/json"
}

# Processar texto
response = requests.post(
    f"{api_url}/v2/processing/text",
    headers=headers,
    json={
        "text": "Olá, Mundo! Hello, World! こんにちは世界！",
        "font_name": "NotoSans-Regular",
        "size": 32,
        "max_width": 800,
        "language": "multi",
        "color": (0, 0, 0),
        "alignment": "center"
    }
)

if response.status_code == 200:
    result = response.json()
    
    # Salvar imagem
    with open("texto_renderizado.png", "wb") as f:
        f.write(result["image"])
        
    print(f"Métricas: {result['metrics']}")
    print(f"Idioma detectado: {result['language']}")
```

## Processamento de Imagem

### Aplicar Filtros e Efeitos

```python
import requests
from PIL import Image
import io

# Configuração
api_url = "http://localhost:8000"
headers = {
    "Authorization": f"Bearer {seu_token}"
}

# Preparar imagem
files = {
    "file": ("imagem.jpg", open("imagem.jpg", "rb"), "image/jpeg")
}

# Definir operações
operations = {
    "operations": [
        {
            "type": "resize",
            "params": {
                "width": 800,
                "height": 600,
                "method": "LANCZOS"
            }
        },
        {
            "type": "filter",
            "params": {
                "name": "gaussian",
                "kernel": (5, 5),
                "sigma": 1.0
            }
        },
        {
            "type": "effect",
            "params": {
                "name": "sketch",
                "sigma": 0.5,
                "angle": 45
            }
        }
    ],
    "output_format": "PIL"
}

# Processar imagem
response = requests.post(
    f"{api_url}/v2/processing/image",
    headers=headers,
    files=files,
    data={"request": json.dumps(operations)}
)

if response.status_code == 200:
    result = response.json()
    
    # Salvar imagem processada
    with open("imagem_processada.png", "wb") as f:
        f.write(result["processed_image"])
```

### Processamento em Batch

```python
import requests
import json
from pathlib import Path

# Configuração
api_url = "http://localhost:8000"
headers = {
    "Authorization": f"Bearer {seu_token}"
}

# Preparar arquivos
files = [
    ("files", (f.name, open(f, "rb"), "image/jpeg"))
    for f in Path("imagens").glob("*.jpg")
]

# Definir operações
operations = {
    "operations": [
        {
            "type": "resize",
            "params": {
                "width": 1024,
                "height": 1024
            }
        },
        {
            "type": "filter",
            "params": {
                "name": "median",
                "kernel": 3
            }
        }
    ],
    "output_format": "PIL"
}

# Processar imagens em batch
response = requests.post(
    f"{api_url}/v2/processing/batch",
    headers=headers,
    files=files,
    data={"request": json.dumps(operations)}
)

if response.status_code == 200:
    results = response.json()
    
    # Salvar imagens processadas
    for result in results:
        output_path = f"processadas/{result['filename']}"
        with open(output_path, "wb") as f:
            f.write(result["processed_image"])
```

## Exemplos de Operações

### Operações de Imagem Disponíveis

1. Redimensionamento
```json
{
    "type": "resize",
    "params": {
        "width": 800,
        "height": 600,
        "method": "LANCZOS"  // NEAREST, BILINEAR, BICUBIC, LANCZOS
    }
}
```

2. Recorte
```json
{
    "type": "crop",
    "params": {
        "box": [100, 100, 500, 500]  // [left, top, right, bottom]
    }
}
```

3. Rotação
```json
{
    "type": "rotate",
    "params": {
        "angle": 45,
        "expand": true
    }
}
```

4. Filtros
```json
{
    "type": "filter",
    "params": {
        "name": "gaussian",  // gaussian, median
        "kernel": [5, 5],
        "sigma": 1.0
    }
}
```

5. Detecção
```json
{
    "type": "detection",
    "params": {
        "detector": "face"
    }
}
```

6. Efeitos Especiais
```json
{
    "type": "effect",
    "params": {
        "name": "sketch",  // sketch, oil_paint
        "sigma": 0.5,
        "angle": 45
    }
}
```

7. Composição
```json
{
    "type": "composite",
    "params": {
        "overlay": "marca_dagua.png",
        "x": 100,
        "y": 100,
        "blend_mode": "overlay"
    }
}
```

## Notas de Uso

1. **Ordem das Operações**: As operações são aplicadas na ordem em que são especificadas na lista.

2. **Formatos de Saída**:
   - `PIL`: Formato PIL (padrão)
   - `CV2`: Formato OpenCV
   - `TENSOR`: Tensor PyTorch

3. **Cache**: O sistema mantém um cache de fontes e modelos para melhor performance.

4. **GPU**: O processamento é automaticamente otimizado para GPU quando disponível.

5. **Limites**:
   - Tamanho máximo de arquivo: 10MB
   - Máximo de arquivos em batch: 20
   - Resolução máxima: 4096x4096

6. **Formatos Suportados**:
   - Imagens: JPG, PNG, WebP
   - Fontes: TTF, OTF

7. **Idiomas**:
   - Suporte completo a Unicode
   - Detecção automática de idioma
   - Layout bidirecional (RTL/LTR)

## Tratamento de Erros

O sistema retorna erros HTTP padrão:

- `400`: Parâmetros inválidos
- `401`: Não autorizado
- `413`: Arquivo muito grande
- `415`: Formato não suportado
- `429`: Muitas requisições
- `500`: Erro interno do servidor

Exemplo de erro:
```json
{
    "detail": "Arquivo muito grande. Máximo permitido: 10MB"
}
``` 