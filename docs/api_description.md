# Media Generation API

API para geração de mídia com suporte a múltiplas GPUs e processamento distribuído.

## Recursos Principais

### Geração de Imagens
- Suporte a SDXL e LoRA
- Upscaling e pós-processamento
- Batch processing otimizado

### Geração de Vídeos
- Animações com Fish Speech
- Transições suaves
- Processamento em GPU

### Síntese de Voz
- Múltiplas vozes e emoções
- Ajuste de velocidade e tom
- Batch processing

## Características Técnicas

### GPU
- Suporte multi-GPU (4x RTX 4090)
- Balanceamento de carga automático
- Monitoramento em tempo real

### Performance
- Cache em múltiplas camadas
- Rate limiting por usuário/GPU
- Processamento assíncrono

### Segurança
- Autenticação JWT
- Rate limiting
- Validação de inputs

## Endpoints

Todos os endpoints seguem o padrão REST e retornam respostas em JSON.
Consulte a documentação Swagger em `/docs` para detalhes completos. 