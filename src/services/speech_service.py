"""
Serviço para geração de áudio com suporte a textos longos e streaming em tempo real.
"""

import asyncio
import logging
import math
from typing import AsyncGenerator, Dict, List, Optional
import nltk
from prometheus_client import Counter, Gauge

from src.core.config import settings
from src.generation.speech.pipeline import SpeechPipeline
from src.core.cache.manager import cache_manager
from src.utils.audio import AudioProcessor

# Configuração do NLTK
nltk.download('punkt')

logger = logging.getLogger(__name__)

# Métricas
LONG_AUDIO_CHUNKS = Counter(
    'speech_long_audio_chunks_total',
    'Número de chunks processados em áudios longos'
)

STREAMING_CLIENTS = Gauge(
    'speech_streaming_clients_active',
    'Número de clientes ativos em streaming'
)

class SpeechService:
    """Serviço para geração de áudio com recursos avançados."""
    
    def __init__(self):
        """Inicializa o serviço."""
        self.pipeline = SpeechPipeline()
        self.audio_processor = AudioProcessor()
        self.cache = cache_manager.get_cache('speech')
        
    async def generate_long_audio(
        self,
        text: str,
        voice_id: str,
        options: Optional[Dict] = None
    ) -> Dict:
        """
        Gera áudio para textos longos dividindo em chunks e concatenando.
        
        Args:
            text: Texto para sintetizar
            voice_id: ID da voz
            options: Opções de geração
            
        Returns:
            Dicionário com resultado e metadados
        """
        try:
            # Configurações padrão
            options = options or {}
            chunk_size = options.get('chunk_size', 400)  # caracteres
            crossfade = options.get('crossfade', 0.3)    # segundos
            
            # Divide o texto em chunks
            chunks = self._split_text(text, chunk_size)
            total_chunks = len(chunks)
            
            logger.info(f"Gerando áudio longo: {total_chunks} chunks")
            
            # Gera áudio para cada chunk
            audio_parts = []
            metadata_parts = []
            
            for i, chunk in enumerate(chunks):
                logger.debug(f"Processando chunk {i+1}/{total_chunks}")
                
                # Gera áudio do chunk
                result = await self.pipeline.generate_speech({
                    'text': chunk,
                    'voice_id': voice_id,
                    **options
                })
                
                audio_parts.append(result['audio_path'])
                metadata_parts.append(result['metadata'])
                
                LONG_AUDIO_CHUNKS.inc()
                
                # Notifica progresso
                if options.get('progress_callback'):
                    await options['progress_callback']({
                        'chunk': i + 1,
                        'total': total_chunks,
                        'progress': ((i + 1) / total_chunks) * 100
                    })
            
            # Concatena os áudios com crossfade
            final_audio = await self.audio_processor.concatenate(
                audio_parts,
                crossfade=crossfade
            )
            
            # Calcula metadados agregados
            total_duration = sum(m['duration'] for m in metadata_parts)
            
            return {
                'status': 'success',
                'audio_path': final_audio,
                'metadata': {
                    'duration': total_duration,
                    'chunks': total_chunks,
                    'text_info': {
                        'original': text,
                        'total_chars': len(text)
                    },
                    'processing_info': {
                        'chunk_size': chunk_size,
                        'crossfade': crossfade
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Erro gerando áudio longo: {e}")
            raise
            
    async def stream_speech(
        self,
        text: str,
        voice_id: str,
        chunk_size: int = 100
    ) -> AsyncGenerator[bytes, None]:
        """
        Gera áudio em tempo real usando streaming.
        
        Args:
            text: Texto para sintetizar
            voice_id: ID da voz
            chunk_size: Tamanho do chunk em caracteres
            
        Yields:
            Chunks de áudio em bytes
        """
        try:
            STREAMING_CLIENTS.inc()
            
            # Divide o texto
            chunks = self._split_text(text, chunk_size)
            
            for chunk in chunks:
                # Gera áudio do chunk
                result = await self.pipeline.generate_speech({
                    'text': chunk,
                    'voice_id': voice_id,
                    'format': 'wav'  # Melhor para streaming
                })
                
                # Processa o áudio para streaming
                stream_chunk = await self.audio_processor.prepare_for_streaming(
                    result['audio_path']
                )
                
                yield stream_chunk
                
                # Pequena pausa para não sobrecarregar
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Erro no streaming de áudio: {e}")
            raise
            
        finally:
            STREAMING_CLIENTS.dec()
            
    def _split_text(self, text: str, chunk_size: int) -> List[str]:
        """
        Divide texto em chunks mantendo sentenças completas.
        
        Args:
            text: Texto para dividir
            chunk_size: Tamanho máximo do chunk
            
        Returns:
            Lista de chunks de texto
        """
        # Usa NLTK para dividir em sentenças
        sentences = nltk.sent_tokenize(text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > chunk_size and current_chunk:
                # Chunk atual está cheio, salva e começa novo
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                # Adiciona sentença ao chunk atual
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Adiciona último chunk se existir
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks
        
    async def estimate_resources(self, text: str) -> Dict:
        """
        Estima recursos necessários para gerar o áudio.
        
        Args:
            text: Texto para análise
            
        Returns:
            Dicionário com estimativas
        """
        # Estimativas baseadas em médias observadas
        chars = len(text)
        words = len(text.split())
        
        estimated_duration = (words / 150) * 60  # 150 palavras por minuto
        chunks = math.ceil(chars / 400)  # 400 chars por chunk
        
        return {
            'estimated_duration': estimated_duration,
            'chunks': chunks,
            'vram_required': chunks * 1.5,  # ~1.5GB por chunk
            'processing_time': chunks * 120  # ~120s por chunk
        } 