# Templates para Redes Sociais

Este documento descreve os templates disponíveis para criação de vídeos para diferentes redes sociais.

## Instagram Reels Promo

Template otimizado para promoções de produtos no Instagram Reels.

### Características
- Duração: 30 segundos
- Formato: 1080x1920 (9:16)
- FPS: 60
- Qualidade: Alta

### Parâmetros Obrigatórios
- `product_images`: Lista de URLs das imagens do produto
- `product_name`: Nome do produto
- `price`: Preço do produto
- `cta_text`: Texto de call-to-action
- `background_music`: URL da música de fundo

### Estrutura
1. Introdução (3s)
   - Título com animação slide-in
2. Showcase do Produto (24s)
   - Carrossel de imagens com transições suaves
   - Preço com animação pulsante
3. Call-to-action (3s)
   - CTA com fundo colorido e animação de escala

### Exemplo de Uso
```python
data = {
    "template": "instagram_reels_promo",
    "params": {
        "product_images": [
            "https://exemplo.com/produto1.jpg",
            "https://exemplo.com/produto2.jpg"
        ],
        "product_name": "Tênis Ultra Confort",
        "price": "R$ 299,90",
        "cta_text": "COMPRE AGORA!",
        "background_music": "https://exemplo.com/musica.mp3"
    }
}
```

## LinkedIn Product Launch

Template profissional para lançamento de produtos no LinkedIn.

### Características
- Duração: 45 segundos
- Formato: 1920x1080 (16:9)
- FPS: 30
- Qualidade: Alta

### Parâmetros Obrigatórios
- `product_name`: Nome do produto
- `key_features`: Lista de características principais
- `company_logo`: URL do logo da empresa
- `background_video`: URL do vídeo de fundo
- `background_music`: URL da música de fundo

### Estrutura
1. Introdução com Logo (5s)
   - Logo da empresa com fade-in
   - Texto "Apresenta" com animação
2. Nome do Produto (5s)
   - Título em destaque com animação de escala
3. Características (30s)
   - Lista de features com ícones e animações
4. Call-to-action (5s)
   - "Disponível Agora" com destaque
   - Link para mais informações

### Exemplo de Uso
```python
data = {
    "template": "linkedin_product_launch",
    "params": {
        "product_name": "Enterprise Suite 2.0",
        "key_features": [
            "Integração com IA",
            "Dashboard em tempo real",
            "Suporte 24/7"
        ],
        "company_logo": "https://exemplo.com/logo.png",
        "background_video": "https://exemplo.com/bg.mp4",
        "background_music": "https://exemplo.com/corporate.mp3"
    }
}
```

## Twitter Product Teaser

Template dinâmico para teaser de produtos no Twitter.

### Características
- Duração: 15 segundos
- Formato: 1280x720 (16:9)
- FPS: 30
- Qualidade: Alta

### Parâmetros Obrigatórios
- `product_image`: URL da imagem do produto
- `teaser_text`: Texto principal do teaser
- `launch_date`: Data de lançamento
- `background_music`: URL da música de fundo

### Estrutura
1. Texto Teaser (5s)
   - Animação typewriter do texto principal
2. Imagem do Produto (7s)
   - Reveal animation da imagem
3. Data de Lançamento (3s)
   - "Em breve" com fade-in
   - Data com animação de escala

### Exemplo de Uso
```python
data = {
    "template": "twitter_product_teaser",
    "params": {
        "product_image": "https://exemplo.com/produto.jpg",
        "teaser_text": "Prepare-se para uma nova era em tecnologia",
        "launch_date": "15 de Março",
        "background_music": "https://exemplo.com/teaser.mp3"
    }
}
```

## Dicas de Uso

### Otimização de Mídia
- Imagens: Use formato .jpg para fotos e .png para logos/elementos com transparência
- Vídeos: Comprima os vídeos mantendo boa qualidade (sugerimos H.264)
- Áudio: Use formato .mp3 com bitrate de 192kbps para melhor compatibilidade

### Melhores Práticas
1. **Duração**
   - Instagram Reels: Mantenha em 30s para melhor engajamento
   - LinkedIn: 45s é ideal para conteúdo profissional
   - Twitter: 15s para manter a atenção

2. **Texto**
   - Use fontes legíveis e tamanhos adequados
   - Mantenha textos curtos e diretos
   - Considere legendas para acessibilidade

3. **Música**
   - Use músicas livres de direitos autorais
   - Ajuste o volume para não sobrepor narrações
   - Escolha o estilo de acordo com a rede social

4. **Animações**
   - Mantenha transições suaves e profissionais
   - Evite animações muito chamativas no LinkedIn
   - Use animações dinâmicas para Instagram e Twitter

### Personalização
Todos os templates aceitam personalização através do parâmetro `style`:

```python
"style": {
    "colors": {
        "primary": "#FF0000",
        "secondary": "#000000"
    },
    "fonts": {
        "title": "Montserrat-Bold",
        "body": "Roboto-Regular"
    }
}
``` 