# Template para Anúncios de Produtos

Este documento descreve o template otimizado para criação de anúncios de produtos com foco em conversão.

## Visão Geral

O template `product_ad` foi desenvolvido para criar anúncios de produtos profissionais e envolventes, com foco em destacar características do produto e gerar conversão através de elementos visuais dinâmicos e call-to-actions efetivos.

### Características Principais
- Duração: 30 segundos
- Formato: 1920x1080 (Full HD)
- FPS: 30
- Qualidade: Alta
- Otimizado para: YouTube Ads, Facebook Ads, Display Ads

## Parâmetros

### Parâmetros Obrigatórios
- `product_name`: Nome do produto
- `product_images`: Lista de URLs das imagens do produto
- `price`: Preço original
- `discount_price`: Preço com desconto
- `features`: Lista de características do produto
- `cta_text`: Texto do call-to-action
- `background_music`: URL da música de fundo

### Parâmetros Opcionais
```json
"branding": {
    "logo": "URL do logo",
    "colors": {
        "primary": "Cor primária (hex)",
        "secondary": "Cor secundária (hex)"
    }
}
```

## Estrutura do Vídeo

### 1. Introdução (3 segundos)
- Apresentação do nome do produto
- Animação slide-in do título
- Estabelece a identidade visual

### 2. Showcase do Produto (12 segundos)
- Carrossel de imagens do produto
- Lista de características com animações
- Layout dividido para melhor visualização

### 3. Preços e Oferta (5 segundos)
- Exibição do preço original (riscado)
- Destaque para o preço com desconto
- Selo "OFERTA ESPECIAL" com animação

### 4. Call-to-action (10 segundos)
- CTA com fundo gradiente
- Animação pulsante para chamar atenção
- Texto de urgência

## Elementos Visuais

### Carrossel de Imagens
```json
"style": {
    "size": {
        "width": 800,
        "height": 800
    },
    "border": {
        "color": "#FFFFFF",
        "width": 4,
        "radius": 20
    },
    "shadow": {
        "color": "#00000066",
        "blur": 20
    }
}
```

### Lista de Características
```json
"feature": {
    "fontSize": 32,
    "color": "#FFFFFF",
    "icon": {
        "type": "checkmark",
        "color": "#4CAF50"
    },
    "animation": {
        "type": "slide",
        "stagger": 0.2
    }
}
```

### Preços
```json
"price": {
    "fontSize": 48,
    "color": "#999999",
    "textDecoration": "line-through"
},
"discount_price": {
    "fontSize": 96,
    "color": "#FF4D4D",
    "animation": {
        "type": "scale"
    }
}
```

## Áudio

### Música de Fundo
- Volume: 30% do volume total
- Fade in/out: 0.5 segundos
- Recomendação: Música energética e profissional

### Efeitos Sonoros
1. Transições
   - Som suave de whoosh
   - Volume: 20%
2. Preço
   - Som de caixa registradora
   - Timing: 15 segundos
   - Volume: 40%

## Efeitos e Filtros

### Filtros de Vídeo
```json
"filters": {
    "brightness": 1.1,
    "contrast": 1.2,
    "saturation": 1.1
}
```

### Transições
- Tipo: Fade
- Duração: 0.3 segundos

### Overlay
- Ruído sutil para textura
- Opacidade: 2%

## Exemplo de Uso

```python
data = {
    "template": "product_ad",
    "params": {
        "product_name": "Smartphone XYZ Pro",
        "product_images": [
            "https://exemplo.com/xyz-front.jpg",
            "https://exemplo.com/xyz-back.jpg",
            "https://exemplo.com/xyz-detail.jpg"
        ],
        "price": "R$ 2.999,00",
        "discount_price": "R$ 2.499,00",
        "features": [
            "Câmera 108MP",
            "5G Ultra-rápido",
            "Bateria 5000mAh",
            "Tela AMOLED 120Hz"
        ],
        "cta_text": "COMPRE AGORA",
        "background_music": "https://exemplo.com/energetic.mp3",
        "branding": {
            "logo": "https://exemplo.com/logo.png",
            "colors": {
                "primary": "#FF4D4D",
                "secondary": "#4CAF50"
            }
        }
    }
}
```

## Melhores Práticas

### Imagens
1. **Qualidade**
   - Resolução mínima: 1200x1200 pixels
   - Formato: JPG para fotos, PNG para elementos com transparência
   - Compressão: Otimizada para web

2. **Composição**
   - Fundo limpo e profissional
   - Iluminação adequada
   - Múltiplos ângulos do produto

### Texto
1. **Produto**
   - Nome claro e direto
   - Evite nomes muito longos

2. **Características**
   - Máximo 4-5 features
   - Frases curtas e impactantes
   - Benefícios tangíveis

3. **CTA**
   - Texto direto e acionável
   - Palavras de urgência
   - Fonte legível e contrastante

### Áudio
1. **Música**
   - Estilo adequado ao produto
   - Sem direitos autorais
   - Ritmo que mantenha interesse

2. **Efeitos**
   - Uso moderado
   - Sincronização com animações
   - Volume balanceado

## Personalização

### Cores
- Use cores da marca
- Mantenha contraste adequado
- Considere psicologia das cores

### Fontes
- Padrão: Montserrat
- Títulos: Bold/Black
- Texto: Regular/SemiBold

### Animações
- Suaves e profissionais
- Timing adequado
- Evite excessos

## Otimização

### Performance
- Comprima assets
- Otimize transições
- Monitore tempo de renderização

### Compatibilidade
- Teste em diferentes plataformas
- Verifique requisitos de ads
- Valide formatos de exportação 