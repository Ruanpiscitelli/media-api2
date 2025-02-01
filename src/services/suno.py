"""
Serviço para integração com o Suno AI.
Gerencia geração de música e voz cantada usando os modelos do Suno.
"""

import asyncio
import logging
import json
import os
from typing import Dict, List, Optional, Any
import torch
import torchaudio
import uuid
from datetime import datetime
from pathlib import Path

from src.core.config import settings
from src.core.cache.manager import cache_manager
from src.core.gpu_manager import gpu_manager
from src.core.queue_manager import queue_manager
from src.utils.audio import AudioProcessor
from src.generation.suno.bark_voice import BarkVoiceModel
from src.generation.suno.musicgen import MusicGenModel

logger = logging.getLogger(__name__)

class SunoService:
    """Serviço para geração de música e voz usando Suno AI."""
    
    def __init__(self):
        """Inicializa o serviço."""
        self.cache = cache_manager.get_cache('suno')
        self.audio_processor = AudioProcessor()
        self.active_tasks: Dict[str, Dict] = {}
        
        # Carregar configurações
        self.config = self._load_config()
        
        # Inicializar modelos
        self.music_model = None
        self.voice_model = None
        
        # Criar diretórios
        Path(settings.SUNO_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path(settings.SUNO_CACHE_DIR).mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> Dict:
        """Carrega configurações do Suno."""
        config_path = os.path.join("config", "suno.json")
        with open(config_path) as f:
            return json.load(f)

    async def _load_music_model(self, device: torch.device):
        """Carrega modelo de geração de música."""
        if self.music_model is None:
            self.music_model = MusicGenModel(
                model_name=self.config["music"]["model_name"],
                device=device
            )
            await self.music_model.load()

    async def _load_voice_model(self, device: torch.device):
        """Carrega modelo de voz."""
        if self.voice_model is None:
            self.voice_model = BarkVoiceModel(
                model_name=self.config["voice"]["model_name"],
                device=device
            )
            await self.voice_model.load()

    async def estimate_resources(self, duration: int) -> Dict:
        """
        Estima recursos necessários para geração.
        
        Args:
            duration: Duração em segundos
            
        Returns:
            Dicionário com estimativas
        """
        # Estimativas baseadas em benchmarks
        vram_per_second = 0.5  # GB por segundo
        time_per_second = 2    # Segundos de processamento por segundo de áudio
        
        return {
            'vram_required': duration * vram_per_second,
            'estimated_time': duration * time_per_second
        }

    async def start_music_generation(
        self,
        prompt: str,
        duration: int,
        style: Optional[str] = None,
        tempo: Optional[int] = None,
        key: Optional[str] = None,
        instruments: Optional[List[str]] = None,
        reference_audio: Optional[str] = None,
        options: Optional[Dict] = None,
        user_id: str = None
    ) -> Dict:
        """
        Inicia geração de música.
        
        Args:
            prompt: Descrição da música
            duration: Duração em segundos
            style: Estilo musical
            tempo: BPM
            key: Tom musical
            instruments: Lista de instrumentos
            reference_audio: URL do áudio de referência
            options: Opções avançadas
            user_id: ID do usuário
            
        Returns:
            Informações da tarefa criada
        """
        task_id = str(uuid.uuid4())
        
        # Criar tarefa
        task = {
            'task_id': task_id,
            'type': 'music',
            'status': 'queued',
            'created_at': datetime.now().isoformat(),
            'user_id': user_id,
            'params': {
                'prompt': prompt,
                'duration': duration,
                'style': style,
                'tempo': tempo,
                'key': key,
                'instruments': instruments,
                'reference_audio': reference_audio,
                'options': options
            },
            'progress': 0,
            'result': None,
            'error': None
        }
        
        self.active_tasks[task_id] = task
        return task

    async def process_music_generation(self, task_id: str):
        """
        Processa geração de música em background.
        
        Args:
            task_id: ID da tarefa
        """
        task = self.active_tasks[task_id]
        
        try:
            # Atualizar status
            task['status'] = 'processing'
            
            # Obter GPU
            device = await gpu_manager.get_device()
            
            # Carregar modelo
            await self._load_music_model(device)
            
            # Preparar parâmetros
            params = task['params']
            generation_params = {
                'prompt': params['prompt'],
                'duration': params['duration'],
                'style': params['style'],
                'tempo': params['tempo'],
                'key': params['key'],
                'instruments': params['instruments'],
                'options': params.get('options', {})
            }
            
            # Gerar música
            audio = await self.music_model.generate(**generation_params)
            
            # Processar áudio
            output_path = os.path.join(
                settings.SUNO_OUTPUT_DIR,
                f"music_{task_id}.wav"
            )
            
            await self.audio_processor.save(
                audio,
                output_path,
                sample_rate=44100,
                format='wav'
            )
            
            # Atualizar tarefa
            task['status'] = 'completed'
            task['progress'] = 100
            task['result'] = {
                'url': f"/media/suno/music_{task_id}.wav",
                'duration': params['duration'],
                'metadata': {
                    'prompt': params['prompt'],
                    'style': params['style'],
                    'tempo': params['tempo'],
                    'key': params['key']
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na geração de música: {e}")
            task['status'] = 'failed'
            task['error'] = str(e)
            
        finally:
            # Liberar GPU
            if device:
                await gpu_manager.release_device(device)

    async def start_voice_generation(
        self,
        text: str,
        melody: Optional[str],
        voice_id: str,
        style: Optional[str],
        emotion: str = "neutral",
        pitch_correction: bool = True,
        formant_shift: float = 0.0,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Inicia geração de voz cantada.
        
        Args:
            text: Letra para cantar
            melody: Melodia em MIDI/MusicXML
            voice_id: ID da voz
            style: Estilo vocal
            emotion: Emoção
            pitch_correction: Aplicar correção de pitch
            formant_shift: Ajuste de formantes
            user_id: ID do usuário
            
        Returns:
            Informações da tarefa criada
        """
        task_id = str(uuid.uuid4())
        
        # Criar tarefa
        task = {
            'task_id': task_id,
            'type': 'voice',
            'status': 'queued',
            'created_at': datetime.now().isoformat(),
            'user_id': user_id,
            'params': {
                'text': text,
                'melody': melody,
                'voice_id': voice_id,
                'style': style,
                'emotion': emotion,
                'pitch_correction': pitch_correction,
                'formant_shift': formant_shift
            },
            'progress': 0,
            'result': None,
            'error': None
        }
        
        self.active_tasks[task_id] = task
        return task

    async def process_voice_generation(self, task_id: str):
        """
        Processa geração de voz em background.
        
        Args:
            task_id: ID da tarefa
        """
        task = self.active_tasks[task_id]
        
        try:
            # Atualizar status
            task['status'] = 'processing'
            
            # Obter GPU
            device = await gpu_manager.get_device()
            
            # Carregar modelo
            await self._load_voice_model(device)
            
            # Preparar parâmetros
            params = task['params']
            generation_params = {
                'text': params['text'],
                'melody': params['melody'],
                'voice_id': params['voice_id'],
                'style': params['style'],
                'emotion': params['emotion'],
                'pitch_correction': params['pitch_correction'],
                'formant_shift': params['formant_shift']
            }
            
            # Gerar voz
            audio = await self.voice_model.generate(**generation_params)
            
            # Processar áudio
            output_path = os.path.join(
                settings.SUNO_OUTPUT_DIR,
                f"voice_{task_id}.wav"
            )
            
            await self.audio_processor.save(
                audio,
                output_path,
                sample_rate=44100,
                format='wav'
            )
            
            # Atualizar tarefa
            task['status'] = 'completed'
            task['progress'] = 100
            task['result'] = {
                'url': f"/media/suno/voice_{task_id}.wav",
                'duration': len(audio) / 44100,  # Duração em segundos
                'metadata': {
                    'text': params['text'],
                    'voice_id': params['voice_id'],
                    'style': params['style'],
                    'emotion': params['emotion']
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na geração de voz: {e}")
            task['status'] = 'failed'
            task['error'] = str(e)
            
        finally:
            # Liberar GPU
            if device:
                await gpu_manager.release_device(device)

    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        Obtém status de uma tarefa.
        
        Args:
            task_id: ID da tarefa
            
        Returns:
            Status da tarefa ou None se não encontrada
        """
        task = self.active_tasks.get(task_id)
        if not task:
            return None
            
        return {
            'task_id': task['task_id'],
            'status': task['status'],
            'progress': task['progress'],
            'result': task['result'],
            'error': task['error']
        }

    async def validate_voice(self, voice_id: str) -> bool:
        """
        Valida se uma voz existe e suporta canto.
        
        Args:
            voice_id: ID da voz
            
        Returns:
            True se válida, False caso contrário
        """
        voices = await self.list_voices()
        return any(v['id'] == voice_id and v['can_sing'] for v in voices)

    async def list_voices(
        self,
        style: Optional[str] = None,
        language: Optional[str] = None
    ) -> List[Dict]:
        """
        Lista vozes disponíveis.
        
        Args:
            style: Filtrar por estilo
            language: Filtrar por idioma
            
        Returns:
            Lista de vozes
        """
        # Tentar cache
        cache_key = f"voices_{style}_{language}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
            
        # Carregar vozes
        voices = self.config['voice']['available_voices']
        
        # Aplicar filtros
        if style:
            voices = [v for v in voices if style in v['styles']]
        if language:
            voices = [v for v in voices if v['language'] == language]
            
        # Cachear resultado
        await self.cache.set(cache_key, voices, expire=3600)
        
        return voices

    async def list_styles(self) -> List[Dict]:
        """
        Lista estilos musicais suportados.
        
        Returns:
            Lista de estilos
        """
        # Tentar cache
        cached = await self.cache.get("music_styles")
        if cached:
            return cached
            
        # Carregar estilos
        styles = self.config['music']['available_styles']
        
        # Cachear
        await self.cache.set("music_styles", styles, expire=3600)
        
        return styles

    async def list_instruments(self) -> List[Dict]:
        """
        Lista instrumentos suportados.
        
        Returns:
            Lista de instrumentos
        """
        # Tentar cache
        cached = await self.cache.get("instruments")
        if cached:
            return cached
            
        # Carregar instrumentos
        instruments = self.config['music']['available_instruments']
        
        # Cachear
        await self.cache.set("instruments", instruments, expire=3600)
        
        return instruments

    async def generate_music(self, params: Dict[str, Any]) -> str:
        """
        Gera música com os parâmetros especificados.
        Retorna ID da tarefa.
        """
        task = await self.start_music_generation(
            prompt=params.get('prompt'),
            duration=params.get('duration', 30),
            style=params.get('style'),
            tempo=params.get('tempo'),
            key=params.get('key'),
            instruments=params.get('instruments'),
            reference_audio=params.get('reference_audio'),
            options=params.get('options'),
            user_id=params.get('user_id')
        )
        
        # Iniciar processamento em background
        asyncio.create_task(self.process_music_generation(task['task_id']))
        
        return task['task_id']
        
    async def generate_voice(self, params: Dict[str, Any]) -> str:
        """
        Gera voz cantada com os parâmetros especificados.
        Retorna ID da tarefa.
        """
        task = await self.start_voice_generation(
            text=params['text'],
            melody=params.get('melody'),
            voice_id=params['voice_id'],
            style=params.get('style'),
            emotion=params.get('emotion', 'neutral'),
            pitch_correction=params.get('pitch_correction', True),
            formant_shift=params.get('formant_shift', 0.0),
            user_id=params.get('user_id')
        )
        
        # Iniciar processamento em background
        asyncio.create_task(self.process_voice_generation(task['task_id']))
        
        return task['task_id']
        
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Obtém status de uma tarefa"""
        return await self.get_task_status(task_id)
        
    async def list_voices(self, style: Optional[str] = None, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista vozes disponíveis"""
        return await self.list_voices(style=style, language=language)
        
    async def list_styles(self) -> List[str]:
        """Lista estilos musicais suportados"""
        return await self.list_styles()
        
    async def list_instruments(self) -> List[str]:
        """Lista instrumentos suportados"""
        return await self.list_instruments()