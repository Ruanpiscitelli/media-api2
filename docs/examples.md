# Exemplos de Uso da API

## 🔍 Índice

1. [Python](#python)
2. [JavaScript](#javascript)
3. [cURL](#curl)
4. [Workflows Comuns](#workflows-comuns)

## Python

### Cliente Básico
```python
import requests
import json
from typing import Optional, Dict, Any

class MediaAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token: Optional[str] = None
    
    def login(self, username: str, password: str) -> bool:
        """Faz login e obtém token."""
        response = requests.post(
            f"{self.base_url}/v2/auth/login",
            json={
                "username": username,
                "password": password
            }
        )
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            return True
        return False
    
    @property
    def headers(self) -> Dict[str, str]:
        """Headers para requisições autenticadas."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        **kwargs
    ) -> Dict[str, Any]:
        """Gera uma imagem."""
        response = requests.post(
            f"{self.base_url}/generate/image",
            headers=self.headers,
            json={
                "prompt": prompt,
                "width": width,
                "height": height,
                **kwargs
            }
        )
        return response.json()
    
    def generate_video(
        self,
        prompt: str,
        num_frames: int = 30,
        fps: int = 24,
        **kwargs
    ) -> Dict[str, Any]:
        """Gera um vídeo."""
        response = requests.post(
            f"{self.base_url}/generate/video",
            headers=self.headers,
            json={
                "prompt": prompt,
                "num_frames": num_frames,
                "fps": fps,
                **kwargs
            }
        )
        return response.json()
    
    def synthesize_speech(
        self,
        text: str,
        voice_id: str = "pt_br_female",
        emotion: str = "neutral",
        **kwargs
    ) -> Dict[str, Any]:
        """Sintetiza voz."""
        response = requests.post(
            f"{self.base_url}/synthesize/speech",
            headers=self.headers,
            json={
                "text": text,
                "voice_id": voice_id,
                "emotion": emotion,
                **kwargs
            }
        )
        return response.json()

# Exemplo de uso
if __name__ == "__main__":
    client = MediaAPIClient("http://api.exemplo.com")
    
    # Login
    if client.login("usuario", "senha"):
        # Gerar imagem
        result = client.generate_image(
            prompt="uma paisagem futurista",
            negative_prompt="baixa qualidade",
            num_inference_steps=30
        )
        print(f"Imagem gerada: {result['url']}")
        
        # Gerar vídeo
        result = client.generate_video(
            prompt="uma cidade futurista à noite",
            num_frames=60,
            fps=30
        )
        print(f"Vídeo gerado: {result['url']}")
        
        # Sintetizar voz
        result = client.synthesize_speech(
            text="Olá, como você está?",
            voice_id="pt_br_female",
            emotion="happy"
        )
        print(f"Áudio gerado: {result['url']}")
```

## JavaScript

### Cliente com Fetch API
```javascript
class MediaAPIClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.token = null;
    }
    
    async login(username, password) {
        const response = await fetch(`${this.baseUrl}/v2/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        if (response.ok) {
            const data = await response.json();
            this.token = data.access_token;
            return true;
        }
        return false;
    }
    
    get headers() {
        return {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
        };
    }
    
    async generateImage(prompt, options = {}) {
        const response = await fetch(`${this.baseUrl}/generate/image`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                prompt,
                width: options.width || 1024,
                height: options.height || 1024,
                ...options
            })
        });
        
        return response.json();
    }
    
    async generateVideo(prompt, options = {}) {
        const response = await fetch(`${this.baseUrl}/generate/video`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                prompt,
                num_frames: options.numFrames || 30,
                fps: options.fps || 24,
                ...options
            })
        });
        
        return response.json();
    }
    
    async synthesizeSpeech(text, options = {}) {
        const response = await fetch(`${this.baseUrl}/synthesize/speech`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                text,
                voice_id: options.voiceId || 'pt_br_female',
                emotion: options.emotion || 'neutral',
                ...options
            })
        });
        
        return response.json();
    }
}

// Exemplo de uso
async function main() {
    const client = new MediaAPIClient('http://api.exemplo.com');
    
    try {
        // Login
        if (await client.login('usuario', 'senha')) {
            // Gerar imagem
            const imageResult = await client.generateImage(
                'uma paisagem futurista',
                {
                    negative_prompt: 'baixa qualidade',
                    num_inference_steps: 30
                }
            );
            console.log(`Imagem gerada: ${imageResult.url}`);
            
            // Gerar vídeo
            const videoResult = await client.generateVideo(
                'uma cidade futurista à noite',
                {
                    numFrames: 60,
                    fps: 30
                }
            );
            console.log(`Vídeo gerado: ${videoResult.url}`);
            
            // Sintetizar voz
            const speechResult = await client.synthesizeSpeech(
                'Olá, como você está?',
                {
                    voiceId: 'pt_br_female',
                    emotion: 'happy'
                }
            );
            console.log(`Áudio gerado: ${speechResult.url}`);
        }
    } catch (error) {
        console.error('Erro:', error);
    }
}

main();
```

## cURL

### Scripts de Exemplo
```bash
#!/bin/bash

# Configurações
API_URL="http://api.exemplo.com"
USERNAME="usuario"
PASSWORD="senha"

# Login e obter token
TOKEN=$(curl -s -X POST "${API_URL}/v2/auth/login" \
     -H "Content-Type: application/json" \
     -d "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}" \
     | jq -r '.access_token')

# Gerar imagem
curl -X POST "${API_URL}/generate/image" \
     -H "Authorization: Bearer ${TOKEN}" \
     -H "Content-Type: application/json" \
     -d '{
         "prompt": "uma paisagem futurista",
         "negative_prompt": "baixa qualidade",
         "width": 1024,
         "height": 1024,
         "num_inference_steps": 30
     }'

# Gerar vídeo
curl -X POST "${API_URL}/generate/video" \
     -H "Authorization: Bearer ${TOKEN}" \
     -H "Content-Type: application/json" \
     -d '{
         "prompt": "uma cidade futurista à noite",
         "num_frames": 60,
         "fps": 30
     }'

# Sintetizar voz
curl -X POST "${API_URL}/synthesize/speech" \
     -H "Authorization: Bearer ${TOKEN}" \
     -H "Content-Type: application/json" \
     -d '{
         "text": "Olá, como você está?",
         "voice_id": "pt_br_female",
         "emotion": "happy"
     }'
```

## Workflows Comuns

### Geração de Imagem com SDXL
```json
{
    "workflow": {
        "nodes": [
            {
                "id": 1,
                "type": "SDXLLoader",
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors"
                }
            },
            {
                "id": 2,
                "type": "CLIPTextEncode",
                "inputs": {
                    "text": "uma paisagem futurista",
                    "clip": ["1", 0]
                }
            },
            {
                "id": 3,
                "type": "CLIPTextEncode",
                "inputs": {
                    "text": "baixa qualidade",
                    "clip": ["1", 1]
                }
            },
            {
                "id": 4,
                "type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "steps": 30,
                    "cfg": 7.5,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "karras",
                    "denoise": 1.0,
                    "seed": 42
                }
            }
        ]
    },
    "timeout": 300,
    "priority": 1
}
```

### Geração de Vídeo com FastHunyuan
```json
{
    "workflow": {
        "nodes": [
            {
                "id": 1,
                "type": "FastHunyuanLoader",
                "inputs": {
                    "ckpt_name": "FastHunyuan.safetensors"
                }
            },
            {
                "id": 2,
                "type": "MotionModule",
                "inputs": {
                    "frames": 30,
                    "motion_scale": 1.0,
                    "model": ["1", 0]
                }
            },
            {
                "id": 3,
                "type": "VideoEncoder",
                "inputs": {
                    "frames": ["2", 0],
                    "fps": 24,
                    "format": "mp4",
                    "quality": "high"
                }
            }
        ]
    },
    "timeout": 600,
    "priority": 2
}
```

### Síntese de Voz com Fish Speech
```json
{
    "workflow": {
        "nodes": [
            {
                "id": 1,
                "type": "FishSpeechLoader",
                "inputs": {
                    "model_path": "fish_speech_1.5.safetensors"
                }
            },
            {
                "id": 2,
                "type": "TextPreprocessor",
                "inputs": {
                    "text": "Olá, como você está?",
                    "language": "pt-BR"
                }
            },
            {
                "id": 3,
                "type": "VoiceSynthesizer",
                "inputs": {
                    "model": ["1", 0],
                    "text": ["2", 0],
                    "voice_id": "pt_br_female",
                    "emotion": "happy",
                    "speed": 1.0
                }
            }
        ]
    },
    "timeout": 120,
    "priority": 1
}
``` 