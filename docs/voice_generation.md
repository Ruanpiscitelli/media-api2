# 🎙️ Sistema de Geração de Voz

Este documento descreve as funcionalidades e endpoints disponíveis para geração, clonagem e gerenciamento de vozes no sistema.

## 📚 Índice
1. [Conceitos Básicos](#conceitos-básicos)
2. [Vozes Pré-definidas](#vozes-pré-definidas)
3. [Clonagem de Voz](#clonagem-de-voz)
4. [Gerenciamento de Vozes](#gerenciamento-de-vozes)
5. [Exemplos de Uso](#exemplos-de-uso)

## Conceitos Básicos

O sistema de geração de voz utiliza o Fish Speech como base, permitindo:
- Síntese de voz a partir de texto
- Clonagem de voz a partir de amostras de áudio
- Controle fino de parâmetros como emoção, velocidade e tom
- Gerenciamento de vozes personalizadas

## Vozes Pré-definidas

### Listar Vozes Disponíveis
```http
GET /v2/voices/list
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "voices": [
        {
            "id": "pt_br_female_1",
            "name": "Ana",
            "language": "pt-BR",
            "gender": "female",
            "description": "Voz feminina profissional",
            "tags": ["clara", "profissional"],
            "preview_url": "https://exemplo.com/voices/ana_preview.mp3"
        },
        {
            "id": "pt_br_male_1",
            "name": "João",
            "language": "pt-BR",
            "gender": "male",
            "description": "Voz masculina jovem",
            "tags": ["jovem", "energético"],
            "preview_url": "https://exemplo.com/voices/joao_preview.mp3"
        }
    ]
}
```

### Detalhes da Voz
```http
GET /v2/voices/{voice_id}
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "id": "pt_br_female_1",
    "name": "Ana",
    "language": "pt-BR",
    "gender": "female",
    "description": "Voz feminina profissional",
    "tags": ["clara", "profissional"],
    "preview_url": "https://exemplo.com/voices/ana_preview.mp3",
    "capabilities": {
        "emotions": ["neutral", "happy", "sad", "angry"],
        "speed_range": [0.5, 2.0],
        "pitch_range": [-10, 10]
    },
    "samples": [
        {
            "text": "Olá, como posso ajudar?",
            "audio_url": "https://exemplo.com/voices/ana_sample1.mp3"
        }
    ]
}
```

## Clonagem de Voz

### Iniciar Processo de Clonagem
```http
POST /v2/voices/clone
Content-Type: multipart/form-data
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "name": "Minha Voz",
    "description": "Clonagem da minha voz",
    "language": "pt-BR",
    "gender": "female",
    "samples": [
        {
            "audio": <arquivo_audio1.wav>,
            "text": "Transcrição do áudio 1"
        },
        {
            "audio": <arquivo_audio2.wav>,
            "text": "Transcrição do áudio 2"
        }
    ],
    "settings": {
        "quality": "high",
        "preserve_pronunciation": true
    }
}
```

**Resposta (202 Accepted)**
```json
{
    "clone_id": "clone_123",
    "status": "processing",
    "estimated_time": 300,
    "progress": 0
}
```

### Verificar Status da Clonagem
```http
GET /v2/voices/clone/{clone_id}/status
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "clone_id": "clone_123",
    "status": "completed",
    "progress": 100,
    "voice_id": "custom_voice_123",
    "preview_url": "https://exemplo.com/voices/custom_123_preview.mp3"
}
```

## Gerenciamento de Vozes

### Adicionar Nova Voz
```http
POST /v2/voices/add
Content-Type: multipart/form-data
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "name": "Nova Voz",
    "description": "Descrição da nova voz",
    "language": "pt-BR",
    "gender": "female",
    "model_file": <arquivo_modelo.pth>,
    "config_file": <arquivo_config.json>,
    "preview_audio": <arquivo_preview.mp3>,
    "tags": ["profissional", "clara"]
}
```

### Atualizar Voz Existente
```http
PUT /v2/voices/{voice_id}
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "name": "Nome Atualizado",
    "description": "Descrição atualizada",
    "tags": ["tag1", "tag2"]
}
```

### Remover Voz
```http
DELETE /v2/voices/{voice_id}
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

## Exemplos de Uso

### Geração Básica
```http
POST /v2/synthesize/speech
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "text": "Olá, como posso ajudar você hoje?",
    "voice_id": "pt_br_female_1",
    "emotion": "happy",
    "speed": 1.0,
    "pitch": 0
}
```

### Geração com Voz Clonada
```http
POST /v2/synthesize/speech
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "text": "Esta é uma demonstração da minha voz clonada",
    "voice_id": "custom_voice_123",
    "emotion": "neutral",
    "speed": 1.0,
    "pitch": 0,
    "preserve_characteristics": true
}
```

### Geração em Lote
```http
POST /v2/synthesize/speech/batch
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "items": [
        {
            "text": "Primeiro texto para sintetizar",
            "voice_id": "pt_br_female_1",
            "emotion": "neutral"
        },
        {
            "text": "Segundo texto com voz diferente",
            "voice_id": "custom_voice_123",
            "emotion": "happy"
        }
    ],
    "output_format": "mp3",
    "quality": "high"
}
```

### Geração com Estilos Avançados
```http
POST /v2/synthesize/speech/styled
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "text": "Texto para sintetizar com estilo personalizado",
    "voice_id": "pt_br_female_1",
    "style": {
        "emotion": "happy",
        "intensity": 0.8,
        "speaking_rate": 1.2,
        "pitch_variation": 0.3,
        "emphasis": {
            "words": ["personalizado"],
            "strength": 1.5
        }
    },
    "audio_effects": {
        "reverb": 0.2,
        "compression": true,
        "normalization": true
    }
}
```

## Requisitos para Clonagem de Voz

### Requisitos de Áudio
- **Formatos suportados**: WAV, MP3, FLAC
- **Taxa de amostragem**: Mínimo 16kHz, recomendado 24kHz
- **Duração por amostra**: 3-15 segundos
- **Quantidade de amostras**:
  - Mínimo: 3 amostras
  - Recomendado: 10 amostras
  - Máximo: 50 amostras

### Qualidade das Amostras
- Áudio limpo sem ruído de fundo
- Fala clara e bem articulada
- Volume consistente
- Sem efeitos ou processamento
- Gravação em ambiente silencioso

### Transcrições
- Texto preciso do conteúdo falado
- Pontuação correta
- Sem abreviações
- Números escritos por extenso

## Emoções Disponíveis

O sistema suporta as seguintes emoções:
- `neutral` (padrão)
- `happy`
- `sad`
- `angry`
- `surprised`
- `fear`

Cada emoção pode ser ajustada com um valor de intensidade de 0.0 a 1.0.

## Parâmetros Avançados

### Controle de Voz
```json
{
    "temperature": 0.667,     // Controle de variabilidade (0.0-1.0)
    "length_scale": 1.0,      // Velocidade de fala (0.5-2.0)
    "noise_scale": 0.667,     // Naturalidade da voz (0.0-1.0)
    "emotion_strength": 0.5   // Intensidade da emoção (0.0-1.0)
}
```

### Qualidade de Treinamento
- **Alta Qualidade**:
  - 50 épocas
  - Batch size: 8
  - Learning rate: 0.0001
  - Tempo estimado: 2-4 horas

- **Rápido**:
  - 25 épocas
  - Batch size: 16
  - Learning rate: 0.0002
  - Tempo estimado: 30-60 minutos

## Exemplos de Uso Avançado

### Clonagem com Configurações Personalizadas
```http
POST /v2/voices/clone
Content-Type: multipart/form-data
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "name": "Voz Personalizada",
    "description": "Clonagem com configurações avançadas",
    "language": "pt-BR",
    "gender": "female",
    "samples": [
        {
            "audio": <arquivo_audio1.wav>,
            "text": "Texto do primeiro áudio de exemplo"
        },
        {
            "audio": <arquivo_audio2.wav>,
            "text": "Segundo exemplo de áudio para clonagem"
        }
    ],
    "settings": {
        "quality": "high",
        "preserve_pronunciation": true,
        "training": {
            "epochs": 75,
            "batch_size": 4,
            "learning_rate": 0.00005
        },
        "audio": {
            "sample_rate": 24000,
            "mel_channels": 80
        }
    }
}
```

### Geração com Controle Fino
```http
POST /v2/synthesize/speech/styled
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "text": "Este é um exemplo de texto com controle fino de estilo",
    "voice_id": "custom_voice_123",
    "style": {
        "emotion": "happy",
        "emotion_strength": 0.8,
        "speaking_rate": 1.2,
        "pitch_variation": 0.3,
        "emphasis": {
            "words": ["exemplo", "controle", "estilo"],
            "strength": 1.5
        }
    },
    "audio_effects": {
        "reverb": 0.2,
        "compression": true,
        "normalization": true
    },
    "generation_params": {
        "temperature": 0.6,
        "length_scale": 1.1,
        "noise_scale": 0.7
    }
}
```

### Geração em Lote com Diferentes Estilos
```http
POST /v2/synthesize/speech/batch
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "items": [
        {
            "text": "Primeiro texto com estilo feliz",
            "voice_id": "custom_voice_123",
            "emotion": "happy",
            "emotion_strength": 0.8,
            "speaking_rate": 1.2
        },
        {
            "text": "Segundo texto com estilo triste",
            "voice_id": "custom_voice_123",
            "emotion": "sad",
            "emotion_strength": 0.6,
            "speaking_rate": 0.9
        }
    ],
    "output_format": "mp3",
    "quality": "high",
    "audio_processing": {
        "normalize": true,
        "remove_silence": true
    }
}
```

## Recomendações de Uso

### Otimização de Performance
1. **Clonagem de Voz**:
   - Use 10-15 amostras de áudio de alta qualidade
   - Mantenha as amostras entre 5-10 segundos
   - Distribua as amostras em diferentes tons e velocidades

2. **Geração de Voz**:
   - Textos longos (>500 caracteres) devem ser divididos
   - Use pontuação adequada para melhor naturalidade
   - Ajuste os parâmetros gradualmente

3. **Batch Processing**:
   - Limite o lote a 10 itens por requisição
   - Monitore o uso de GPU
   - Use qualidade apropriada para o caso de uso

### Melhores Práticas
1. **Preparação de Amostras**:
   - Grave em ambiente silencioso
   - Use microfone de qualidade
   - Mantenha entonação natural
   - Fale claramente cada palavra

2. **Treinamento**:
   - Comece com configurações padrão
   - Ajuste parâmetros gradualmente
   - Monitore a qualidade do preview
   - Faça backup dos modelos treinados

3. **Produção**:
   - Implemente cache de áudios gerados
   - Monitore uso de recursos
   - Implemente rate limiting
   - Mantenha logs detalhados

## Suporte Multilíngue

O sistema suporta os seguintes idiomas:
- 🇺🇸 Inglês (en-US)
- 🇧🇷 Português (pt-BR)
- 🇯🇵 Japonês (ja-JP)
- 🇰🇷 Coreano (ko-KR)
- 🇨🇳 Chinês (zh-CN)
- 🇫🇷 Francês (fr-FR)
- 🇩🇪 Alemão (de-DE)
- 🇸🇦 Árabe (ar-SA)
- 🇪🇸 Espanhol (es-ES)

### Recursos Cross-Linguais
- Clonagem de voz com transferência entre idiomas
- Detecção automática de idioma
- Preservação de sotaque e características vocais

### Exemplo de Uso Multilíngue
```http
POST /v2/synthesize/speech
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "text": "Hello, this is a multilingual test",
    "voice_id": "pt_br_female_1",
    "target_language": "en-US",
    "preserve_accent": true,
    "translation_config": {
        "enabled": true,
        "preserve_emphasis": true
    }
}
```

## Otimizações de Performance

### Mixed Precision Training
O sistema utiliza treinamento em precisão mista (FP16/FP32) para:
- Redução de uso de memória em até 50%
- Aceleração do treinamento em até 2x
- Manutenção da qualidade do áudio

### Cache e Quantização
- Cache de modelos mais utilizados
- Quantização INT8 para inferência
- Otimização de memória GPU

### Exemplo de Configuração Otimizada
```http
POST /v2/voices/clone
Content-Type: multipart/form-data
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    // ... outros campos ...
    "optimization_config": {
        "mixed_precision": true,
        "model_quantization": true,
        "cache_enabled": true,
        "gpu_optimization": {
            "compile_model": true,
            "memory_efficient": true
        },
        "training": {
            "gradient_accumulation": 4,
            "gradient_clipping": 1.0,
            "weight_decay": 0.01
        }
    }
}
```

### Métricas de Performance
- **RTX 4090**: ~15x tempo real
- **RTX 4060**: ~5x tempo real
- Taxa de erro de caracteres: 2%
- Taxa de erro de palavras: 2%

## Recursos Avançados

### Zero-Shot e Few-Shot Learning
O sistema suporta:
- Clonagem de voz sem amostras (zero-shot)
- Clonagem com poucas amostras (few-shot)
- Adaptação rápida de vozes existentes

### Exemplo de Zero-Shot
```http
POST /v2/voices/clone/zero-shot
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "reference_voice": "custom_voice_123",
    "target_characteristics": {
        "age": "young",
        "gender": "female",
        "style": "professional"
    }
}
```

### Exemplo de Few-Shot
```http
POST /v2/voices/clone/few-shot
Content-Type: multipart/form-data
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

{
    "base_voice": "pt_br_female_1",
    "samples": [
        {
            "audio": <arquivo_curto.wav>,
            "text": "Exemplo curto de voz"
        }
    ],
    "adaptation_config": {
        "quick_adaptation": true,
        "preserve_base_characteristics": true
    }
}
```

## Monitoramento e Métricas

### Métricas de Qualidade
- MOS (Mean Opinion Score)
- PESQ (Perceptual Evaluation of Speech Quality)
- STOI (Short-Time Objective Intelligibility)

### Exemplo de Requisição com Métricas
```http
GET /v2/voices/{voice_id}/metrics
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Resposta (200 OK)**
```json
{
    "voice_id": "custom_voice_123",
    "metrics": {
        "mos": 4.2,
        "pesq": 3.8,
        "stoi": 0.92,
        "character_error_rate": 0.02,
        "word_error_rate": 0.02,
        "real_time_factor": 15.0
    },
    "performance": {
        "average_generation_time": 0.5,
        "gpu_utilization": 85,
        "memory_usage": "4.2GB"
    }
} 