"""
Processador de texto para síntese de voz.
Responsável por normalização, detecção de idioma e fonemização.
"""

import logging
from typing import Dict, List, Optional
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import phonemizer
from phonemizer.backend import EspeakBackend
from phonemizer.separator import Separator
from num2words import num2words

logger = logging.getLogger(__name__)

class TextNormalizer:
    """Normaliza texto para síntese de voz."""
    
    def __init__(self):
        self.number_converter = num2words
        
    def normalize(self, text: str) -> str:
        """
        Normaliza texto convertendo números, símbolos e abreviações.
        
        Args:
            text: Texto a ser normalizado
            
        Returns:
            Texto normalizado
        """
        try:
            # Remove espaços extras
            text = " ".join(text.split())
            
            # Converte números para texto
            text = self._convert_numbers(text)
            
            # Expande abreviações comuns
            text = self._expand_abbreviations(text)
            
            return text
            
        except Exception as e:
            logger.error(f"Erro na normalização: {e}")
            return text
            
    def _convert_numbers(self, text: str) -> str:
        """Converte números para texto por extenso."""
        words = []
        for word in text.split():
            try:
                if word.replace(".", "").replace(",", "").isdigit():
                    word = self.number_converter(int(word), lang="pt-BR")
            except:
                pass
            words.append(word)
        return " ".join(words)
        
    def _expand_abbreviations(self, text: str) -> str:
        """Expande abreviações comuns."""
        abbreviations = {
            "sr.": "senhor",
            "sra.": "senhora",
            "dr.": "doutor",
            "dra.": "doutora",
            # Adicionar mais conforme necessário
        }
        
        for abbr, expansion in abbreviations.items():
            text = text.replace(abbr, expansion)
            text = text.replace(abbr.upper(), expansion)
            
        return text


class TextProcessor:
    """
    Processador completo de texto para síntese de voz.
    Inclui normalização, detecção de idioma e fonemização.
    """
    
    def __init__(self, language_models_path: str = "models/language"):
        """
        Inicializa o processador de texto.
        
        Args:
            language_models_path: Caminho para os modelos de linguagem
        """
        self.language_models_path = language_models_path
        self.text_normalizer = TextNormalizer()
        self.tokenizer = self._load_tokenizer()
        self.language_detector = self._load_language_detector()
        self.phonemizer = self._load_phonemizer()
        
    def _load_tokenizer(self) -> AutoTokenizer:
        """Carrega o tokenizer multilíngue."""
        try:
            return AutoTokenizer.from_pretrained(
                "facebook/mbart-large-50-many-to-many-mmt"
            )
        except Exception as e:
            logger.error(f"Erro carregando tokenizer: {e}")
            raise
            
    def _load_language_detector(self) -> AutoModelForSequenceClassification:
        """Carrega o modelo de detecção de idioma."""
        try:
            return AutoModelForSequenceClassification.from_pretrained(
                "papluca/xlm-roberta-base-language-detection"
            )
        except Exception as e:
            logger.error(f"Erro carregando detector de idioma: {e}")
            raise
            
    def _load_phonemizer(self) -> EspeakBackend:
        """
        Carrega e configura o phonemizer.
        
        Returns:
            EspeakBackend: Backend configurado do phonemizer
        """
        try:
            # Configurar backend do phonemizer
            return EspeakBackend(
                language="pt-BR",
                preserve_punctuation=True,
                with_stress=True,
                separator=Separator(
                    word=' ',
                    syllable='-',
                    phone='|'
                )
            )
        except Exception as e:
            logger.error(f"Erro ao carregar phonemizer: {e}")
            raise
            
    def process_text(self, text: str, language: Optional[str] = None) -> Dict:
        """
        Processa o texto para síntese de voz.
        
        Args:
            text: Texto a ser processado
            language: Código do idioma (opcional)
            
        Returns:
            Dicionário com texto processado e metadados
        """
        try:
            # Normalização básica
            normalized_text = self.text_normalizer.normalize(text)
            
            # Detecção de idioma se não especificado
            if not language:
                language = self._detect_language(normalized_text)
                
            # Tokenização específica para o idioma
            tokens = self._tokenize(normalized_text, language)
            
            # Fonemização
            phonemes = self._phonemize(tokens, language)
            
            # Análise de prosódia
            prosody = self._analyze_prosody(normalized_text, language)
            
            return {
                'normalized_text': normalized_text,
                'language': language,
                'tokens': tokens,
                'phonemes': phonemes,
                'prosody': prosody
            }
            
        except Exception as e:
            logger.error(f"Erro no processamento de texto: {e}")
            raise
            
    def _detect_language(self, text: str) -> str:
        """Detecta o idioma do texto."""
        try:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True
            )
            
            with torch.no_grad():
                outputs = self.language_detector(**inputs)
                
            predicted_language = self.language_detector.config.id2label[
                outputs.logits.argmax().item()
            ]
            
            return predicted_language
            
        except Exception as e:
            logger.error(f"Erro na detecção de idioma: {e}")
            return "pt-BR"  # Fallback para português
            
    def _tokenize(self, text: str, language: str) -> List[str]:
        """Tokeniza o texto para o idioma específico."""
        try:
            tokens = self.tokenizer.tokenize(text)
            return tokens
        except Exception as e:
            logger.error(f"Erro na tokenização: {e}")
            return text.split()
            
    def _phonemize(self, tokens: List[str], language: str) -> List[str]:
        """Converte tokens em fonemas."""
        try:
            text = " ".join(tokens)
            phonemes = phonemizer.phonemize(
                text,
                backend=self.phonemizer,
                strip=True
            )
            return phonemes.split()
        except Exception as e:
            logger.error(f"Erro na fonemização: {e}")
            return tokens
            
    def _analyze_prosody(self, text: str, language: str) -> Dict:
        """
        Analisa aspectos prosódicos do texto.
        
        Args:
            text: Texto normalizado
            language: Código do idioma
            
        Returns:
            Dicionário com informações prosódicas
        """
        try:
            # Encontra pontos de pausa
            sentence_breaks = [
                i for i, char in enumerate(text)
                if char in ".!?,:;"
            ]
            
            # Detecta palavras enfatizadas (maiúsculas)
            emphasis = [
                word for word in text.split()
                if word.isupper()
            ]
            
            # Análise básica de entonação
            intonation = []
            for sentence in text.split("."):
                if sentence.strip():
                    if "?" in sentence:
                        intonation.append("rising")
                    elif "!" in sentence:
                        intonation.append("exclamation")
                    else:
                        intonation.append("falling")
            
            return {
                'sentence_breaks': sentence_breaks,
                'emphasis': emphasis,
                'intonation': intonation,
                'language': language
            }
            
        except Exception as e:
            logger.error(f"Erro na análise prosódica: {e}")
            return {
                'sentence_breaks': [],
                'emphasis': [],
                'intonation': [],
                'language': language
            }