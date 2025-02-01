# Exemplos de Uso da API json2video

## 1. Criando uma Intro para YouTube

### Requisição
```python
import requests
import json

url = "https://api.seudominio.com/v2/json2video/create"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer seu_token"
}

data = {
    "template": "youtube_intro",
    "params": {
        "channel_name": "Dev Tips",
        "logo_url": "https://exemplo.com/logo.png",
        "background_video": "https://exemplo.com/bg.mp4",
        "background_music": "https://exemplo.com/music.mp3",
        "color_scheme": {
            "primary": "#FF0000",
            "secondary": "#FFFFFF"
        }
    }
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

### Resposta
```json
{
    "project_id": "yt_intro_123",
    "status": "processing",
    "progress": 0,
    "estimated_time": 30
}
```

## 2. Criando um Story para Instagram

### Requisição
```python
data = {
    "template": "instagram_story",
    "params": {
        "background_media": "https://exemplo.com/background.mp4",
        "title": "Novidades da Semana!",
        "cta_text": "ARRASTE PARA CIMA ⬆️",
        "brand_logo": "https://exemplo.com/brand.png",
        "brand_colors": {
            "primary": "#FF6B6B",
            "secondary": "#4ECDC4"
        }
    }
}

response = requests.post(url, headers=headers, json=data)
```

## 3. Criando um YouTube Short

### Requisição
```python
data = {
    "template": "youtube_shorts",
    "params": {
        "video_url": "https://exemplo.com/video.mp4",
        "captions": [
            {
                "text": "Aprenda a programar em 60 segundos!",
                "time": 0
            },
            {
                "text": "Primeiro, instale Python...",
                "time": 5
            },
            {
                "text": "Agora, abra seu editor favorito...",
                "time": 10
            }
        ],
        "background_music": "https://exemplo.com/background.mp3",
        "style": {
            "caption_color": "#FFFFFF",
            "caption_background": "#000000"
        }
    }
}
```

## 4. Criando um Tutorial TikTok

### Requisição
```python
data = {
    "template": "tiktok_tutorial",
    "params": {
        "steps": [
            {
                "title": "Como Fazer um Bolo",
                "video": "https://exemplo.com/step1.mp4",
                "description": "Misture os ingredientes secos"
            },
            {
                "title": "Passo 2",
                "video": "https://exemplo.com/step2.mp4",
                "description": "Adicione os ovos e o leite"
            },
            {
                "title": "Passo Final",
                "video": "https://exemplo.com/step3.mp4",
                "description": "Asse por 30 minutos"
            }
        ],
        "background_music": "https://exemplo.com/cooking.mp3",
        "creator_info": {
            "username": "@chef_master",
            "avatar": "https://exemplo.com/avatar.jpg"
        }
    }
}
```

## 5. Criando um Slideshow Personalizado

### Requisição
```python
data = {
    "scenes": [
        {
            "duration": 5.0,
            "elements": [
                {
                    "type": "text",
                    "content": "Bem-vindo!",
                    "position": {"x": 0.5, "y": 0.3},
                    "style": {
                        "fontSize": 64,
                        "color": "#FFFFFF",
                        "fontFamily": "Montserrat-Bold",
                        "animation": {
                            "type": "scale",
                            "duration": 1.0
                        }
                    }
                },
                {
                    "type": "image",
                    "content": "https://exemplo.com/image1.jpg",
                    "position": {"x": 0.5, "y": 0.6},
                    "style": {
                        "size": {
                            "width": 800,
                            "height": 600
                        },
                        "animation": {
                            "type": "fade",
                            "duration": 0.5
                        }
                    }
                }
            ],
            "transition": {
                "type": "fade",
                "duration": 1.0
            }
        }
    ],
    "audio": {
        "music": {
            "url": "https://exemplo.com/background.mp3",
            "volume": 0.3,
            "fade": {
                "in": 2.0,
                "out": 2.0
            }
        }
    }
}
```

## 6. Monitorando o Progresso

### Requisição
```python
def check_progress(project_id):
    status_url = f"https://api.seudominio.com/v2/json2video/status/{project_id}"
    
    while True:
        response = requests.get(status_url, headers=headers)
        data = response.json()
        
        print(f"Progresso: {data['progress']}%")
        
        if data['status'] == 'completed':
            print(f"Vídeo pronto: {data['video_url']}")
            break
        elif data['status'] == 'error':
            print(f"Erro: {data.get('error')}")
            break
            
        time.sleep(5)  # Aguarda 5 segundos antes de verificar novamente
```

## 7. Gerando Preview

### Requisição
```python
def generate_preview(project_id, scene_index, time):
    preview_url = f"https://api.seudominio.com/v2/json2video/{project_id}/preview"
    
    data = {
        "scene_index": scene_index,
        "time": time
    }
    
    response = requests.post(preview_url, headers=headers, json=data)
    preview_data = response.json()
    
    print(f"Preview disponível em: {preview_data['preview_url']}")
```

## 8. Tratamento de Erros

```python
def create_video(template, params):
    try:
        response = requests.post(url, headers=headers, json={
            "template": template,
            "params": params
        })
        
        response.raise_for_status()  # Lança exceção para status codes 4xx/5xx
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        if response.status_code == 400:
            print("Erro de validação:", response.json().get('detail'))
        elif response.status_code == 401:
            print("Token inválido ou expirado")
        elif response.status_code == 403:
            print("Limite de requisições excedido")
        elif response.status_code == 404:
            print("Template não encontrado")
        else:
            print("Erro inesperado:", str(e))
        return None
```

## 9. Upload de Arquivos

```python
def upload_media(file_path):
    upload_url = "https://api.seudominio.com/v2/json2video/upload"
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(upload_url, headers=headers, files=files)
        
        if response.status_code == 200:
            return response.json()['url']
        else:
            print("Erro no upload:", response.json().get('detail'))
            return None
```

## 10. Exemplo Completo

```python
def create_social_video(template, media_files, params):
    # Upload de arquivos
    uploaded_urls = {}
    for key, file_path in media_files.items():
        url = upload_media(file_path)
        if url:
            uploaded_urls[key] = url
        else:
            return None
            
    # Atualiza parâmetros com URLs
    for key, url in uploaded_urls.items():
        params[key] = url
        
    # Cria o vídeo
    result = create_video(template, params)
    if not result:
        return None
        
    # Monitora progresso
    project_id = result['project_id']
    check_progress(project_id)
    
    return result

# Uso
media_files = {
    "logo_url": "path/to/logo.png",
    "background_video": "path/to/background.mp4",
    "background_music": "path/to/music.mp3"
}

params = {
    "channel_name": "Dev Tips",
    "color_scheme": {
        "primary": "#FF0000",
        "secondary": "#FFFFFF"
    }
}

result = create_social_video("youtube_intro", media_files, params) 