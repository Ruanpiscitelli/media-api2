# Documentação da API Suno

Esta documentação descreve os endpoints disponíveis para geração de música e voz usando o Suno AI.

## Autenticação

Todos os endpoints requerem autenticação via token JWT no header:

```http
Authorization: Bearer <seu_token>
```

## Endpoints

### Geração de Música

#### POST /v2/suno/generate/music

Gera música usando o modelo MusicGen.

**Request:**
```json
{
    "prompt": "Uma música alegre de jazz com piano e saxofone",
    "duration": 30,
    "style": "jazz",
    "tempo": 120,
    "key": "C",
    "instruments": ["piano", "saxophone"],
    "options": {
        "temperature": 0.7,
        "top_k": 50,
        "top_p": 0.95
    }
}
```

**Parâmetros:**
- `prompt` (string, obrigatório): Descrição da música desejada
- `duration` (int, opcional): Duração em segundos (padrão: 30, min: 10, max: 300)
- `style` (string, opcional): Estilo musical (ver /styles para opções)
- `tempo` (int, opcional): BPM (40-200)
- `key` (string, opcional): Tom musical (ex: C, Am)
- `instruments` (array, opcional): Lista de instrumentos (ver /instruments)
- `options` (object, opcional): Configurações avançadas de geração

**Response (200):**
```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "estimated_time": 60,
    "preview_url": "/media/suno/preview_550e8400.mp3"
}
```

### Geração de Voz

#### POST /v2/suno/generate/voice

Gera voz cantada usando o modelo Bark.

**Request:**
```json
{
    "text": "Letra da música para cantar",
    "melody": "base64_encoded_midi_file",
    "voice_id": "pt_br_female_1",
    "style": "pop",
    "emotion": "happy",
    "pitch_correction": true,
    "formant_shift": 0.0
}
```

**Parâmetros:**
- `text` (string, obrigatório): Texto para cantar
- `melody` (string, opcional): Arquivo MIDI/MusicXML em base64
- `voice_id` (string, obrigatório): ID da voz (ver /voices)
- `style` (string, opcional): Estilo vocal
- `emotion` (string, opcional): Emoção (neutral, happy, sad, angry, tender)
- `pitch_correction` (bool, opcional): Aplicar correção de pitch
- `formant_shift` (float, opcional): Ajuste de formantes (-1.0 a 1.0)

**Response (200):**
```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "estimated_time": 30,
    "preview_url": "/media/suno/preview_550e8400.mp3"
}
```

### Status da Geração

#### GET /v2/suno/status/{task_id}

Verifica o status de uma tarefa de geração.

**Response (200):**
```json
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "progress": 100,
    "result": {
        "url": "/media/suno/music_550e8400.wav",
        "duration": 30,
        "metadata": {
            "prompt": "Uma música alegre de jazz",
            "style": "jazz",
            "tempo": 120,
            "key": "C"
        }
    }
}
```

### Listagem de Vozes

#### GET /v2/suno/voices

Lista vozes disponíveis para canto.

**Query Parameters:**
- `style` (string, opcional): Filtrar por estilo
- `language` (string, opcional): Filtrar por idioma

**Response (200):**
```json
{
    "voices": [
        {
            "id": "pt_br_female_1",
            "name": "Ana",
            "gender": "female",
            "language": "pt-BR",
            "description": "Voz feminina profissional em português",
            "styles": ["pop", "jazz"],
            "can_sing": true,
            "preview_url": "/media/voices/ana_preview.mp3"
        }
    ]
}
```

### Listagem de Estilos

#### GET /v2/suno/styles

Lista estilos musicais suportados.

**Response (200):**
```json
{
    "styles": [
        {
            "id": "classical",
            "name": "Clássico",
            "description": "Música clássica orquestral",
            "instruments": ["strings", "piano", "woodwinds", "brass"]
        }
    ]
}
```

### Listagem de Instrumentos

#### GET /v2/suno/instruments

Lista instrumentos suportados.

**Response (200):**
```json
{
    "instruments": [
        {
            "id": "piano",
            "name": "Piano",
            "category": "keys",
            "styles": ["classical", "jazz", "pop"]
        }
    ]
}
```

## Exemplos de Uso

### Python com aiohttp

```python
import aiohttp
import json
import asyncio

async def generate_music():
    async with aiohttp.ClientSession() as session:
        # Configurar request
        headers = {
            "Authorization": "Bearer seu_token",
            "Content-Type": "application/json"
        }
        
        data = {
            "prompt": "Uma música alegre de jazz com piano e saxofone",
            "duration": 30,
            "style": "jazz",
            "instruments": ["piano", "saxophone"]
        }
        
        # Iniciar geração
        async with session.post(
            "http://api.exemplo.com/v2/suno/generate/music",
            headers=headers,
            json=data
        ) as response:
            result = await response.json()
            task_id = result["task_id"]
            
        # Aguardar conclusão
        while True:
            async with session.get(
                f"http://api.exemplo.com/v2/suno/status/{task_id}",
                headers=headers
            ) as response:
                status = await response.json()
                if status["status"] == "completed":
                    print(f"Música gerada: {status['result']['url']}")
                    break
                elif status["status"] == "failed":
                    print(f"Erro: {status['error']}")
                    break
                await asyncio.sleep(5)

asyncio.run(generate_music())
```

### cURL

```bash
# Gerar música
curl -X POST "http://api.exemplo.com/v2/suno/generate/music" \
  -H "Authorization: Bearer seu_token" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Uma música alegre de jazz com piano e saxofone",
    "duration": 30,
    "style": "jazz",
    "instruments": ["piano", "saxophone"]
  }'

# Verificar status
curl "http://api.exemplo.com/v2/suno/status/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer seu_token"

# Listar vozes
curl "http://api.exemplo.com/v2/suno/voices" \
  -H "Authorization: Bearer seu_token"
```

## Códigos de Erro

- `400 Bad Request`: Parâmetros inválidos ou faltando
- `401 Unauthorized`: Token inválido ou expirado
- `403 Forbidden`: Sem permissão para o recurso
- `404 Not Found`: Recurso não encontrado
- `429 Too Many Requests`: Limite de requisições excedido
- `500 Internal Server Error`: Erro interno do servidor

## Limites e Quotas

- Máximo de 100 requisições por hora por usuário
- Duração máxima de música: 5 minutos
- Tamanho máximo de arquivo MIDI: 10MB
- Armazenamento de arquivos gerados: 24 horas 