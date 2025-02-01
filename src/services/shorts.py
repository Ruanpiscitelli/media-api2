"""
Serviço para geração de YouTube Shorts.
Integra geração de vídeo, música e voz em um pipeline otimizado.
"""

import asyncio
import logging
import json
import os
from typing import Dict, List, Optional
import torch
import uuid
from datetime import datetime
from pathlib import Path
import aiofiles
from fastapi import UploadFile
import yt_dlp
from moviepy.editor import VideoFileClip
import numpy as np

from src.core.config import settings
from src.core.cache.manager import cache_manager
from src.core.gpu_manager import gpu_manager
from src.utils.video import VideoProcessor
from src.generation.suno.musicgen import MusicGenModel
from src.generation.suno.bark_voice import BarkVoiceModel
from src.generation.video.fast_huayuan import FastHuayuanGenerator
from src.core.video_engine import VideoEngine

logger = logging.getLogger(__name__)

class ShortsService:
    """Serviço para geração de YouTube Shorts."""
    
    def __init__(self):
        """Inicializa o serviço."""
        self.cache = cache_manager.get_cache('shorts')
        self.video_processor = VideoProcessor()
        self.video_engine = VideoEngine()
        self.active_tasks: Dict[str, Dict] = {}
        
        # Carregar configurações
        self.config = self._load_config()
        
        # Inicializar modelos
        self.music_model = None
        self.voice_model = None
        self.video_generator = None
        
        # Criar diretórios
        Path(settings.SHORTS_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path(settings.SHORTS_CACHE_DIR).mkdir(parents=True, exist_ok=True)
        Path(settings.SHORTS_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> Dict:
        """Carrega configurações dos shorts."""
        config_path = os.path.join("config", "shorts.json")
        with open(config_path) as f:
            return json.load(f)

    async def _load_models(self, device: torch.device):
        """Carrega modelos necessários."""
        if self.music_model is None:
            self.music_model = MusicGenModel(
                model_name=self.config["music"]["model_name"],
                device=device
            )
            await self.music_model.load()
            
        if self.voice_model is None:
            self.voice_model = BarkVoiceModel(
                model_name=self.config["voice"]["model_name"],
                device=device
            )
            await self.voice_model.load()
            
        if self.video_generator is None:
            self.video_generator = FastHuayuanGenerator(device=device)
            await self.video_generator.load()

    async def estimate_resources(self, duration: int) -> Dict:
        """
        Estima recursos necessários para geração.
        
        Args:
            duration: Duração em segundos
            
        Returns:
            Dicionário com estimativas
        """
        # Estimativas baseadas em benchmarks
        vram_per_second = 1.0  # GB por segundo
        time_per_second = 4    # Segundos de processamento por segundo de vídeo
        
        return {
            'vram_required': duration * vram_per_second,
            'estimated_time': duration * time_per_second
        }

    async def start_generation(
        self,
        title: str,
        description: str,
        duration: int = 60,
        style: str = "cinematic",
        music_prompt: Optional[str] = None,
        voice_id: Optional[str] = None,
        hashtags: Optional[List[str]] = None,
        watermark: Optional[str] = None,
        options: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Inicia geração de um short.
        
        Args:
            title: Título do vídeo
            description: Descrição para gerar o vídeo
            duration: Duração em segundos
            style: Estilo visual
            music_prompt: Prompt para música
            voice_id: ID da voz
            hashtags: Lista de hashtags
            watermark: Texto da marca d'água
            options: Opções avançadas
            user_id: ID do usuário
            
        Returns:
            Informações da tarefa criada
        """
        task_id = str(uuid.uuid4())
        
        # Criar tarefa
        task = {
            'task_id': task_id,
            'type': 'short',
            'status': 'queued',
            'created_at': datetime.now().isoformat(),
            'user_id': user_id,
            'params': {
                'title': title,
                'description': description,
                'duration': duration,
                'style': style,
                'music_prompt': music_prompt,
                'voice_id': voice_id,
                'hashtags': hashtags,
                'watermark': watermark,
                'options': options
            },
            'progress': 0,
            'result': None,
            'error': None
        }
        
        self.active_tasks[task_id] = task
        return task

    async def process_generation(self, task_id: str):
        """
        Processa geração do short em background.
        
        Args:
            task_id: ID da tarefa
        """
        task = self.active_tasks[task_id]
        device = None
        
        try:
            # Atualizar status
            task['status'] = 'processing'
            
            # Obter GPU
            device = await gpu_manager.get_device()
            
            # Carregar modelos
            await self._load_models(device)
            
            # Extrair parâmetros
            params = task['params']
            
            # 1. Gerar vídeo base
            task['progress'] = 10
            video = await self.video_generator.generate_video(
                prompt=params['description'],
                num_frames=params['duration'] * 30,  # 30 fps
                style=params['style']
            )
            
            # 2. Gerar música se solicitado
            task['progress'] = 40
            audio_path = None
            if params['music_prompt']:
                audio = await self.music_model.generate(
                    prompt=params['music_prompt'],
                    duration=params['duration']
                )
                audio_path = os.path.join(
                    settings.SHORTS_OUTPUT_DIR,
                    f"music_{task_id}.wav"
                )
                await self.video_processor.save_audio(audio, audio_path)
            
            # 3. Gerar narração se solicitado
            task['progress'] = 60
            voice_path = None
            if params['voice_id']:
                voice = await self.voice_model.generate(
                    text=params['description'],
                    voice_id=params['voice_id']
                )
                voice_path = os.path.join(
                    settings.SHORTS_OUTPUT_DIR,
                    f"voice_{task_id}.wav"
                )
                await self.video_processor.save_audio(voice, voice_path)
            
            # 4. Compor vídeo final
            task['progress'] = 80
            output_path = os.path.join(
                settings.SHORTS_OUTPUT_DIR,
                f"short_{task_id}.mp4"
            )
            
            # Aplicar template de short
            await self.video_engine.apply_template(
                video_path=video['path'],
                output_path=output_path,
                template=self.config['templates']['default'],
                params={
                    'title': params['title'],
                    'hashtags': params['hashtags'],
                    'watermark': params['watermark'],
                    'background_music': audio_path,
                    'voice': voice_path
                }
            )
            
            # Gerar preview
            preview_path = os.path.join(
                settings.SHORTS_OUTPUT_DIR,
                f"preview_{task_id}.gif"
            )
            await self.video_processor.create_preview(
                video_path=output_path,
                output_path=preview_path,
                duration=3.0
            )
            
            # Atualizar tarefa
            task['status'] = 'completed'
            task['progress'] = 100
            task['result'] = {
                'video_url': f"/media/shorts/short_{task_id}.mp4",
                'preview_url': f"/media/shorts/preview_{task_id}.gif",
                'duration': params['duration'],
                'metadata': {
                    'title': params['title'],
                    'description': params['description'],
                    'style': params['style'],
                    'has_music': audio_path is not None,
                    'has_voice': voice_path is not None
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na geração de short: {e}")
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

    async def save_uploaded_video(
        self,
        file: UploadFile,
        user_id: str
    ) -> str:
        """
        Salva vídeo enviado pelo usuário.
        
        Args:
            file: Arquivo de vídeo
            user_id: ID do usuário
            
        Returns:
            Caminho do vídeo salvo
        """
        try:
            # Gerar nome único
            filename = f"{uuid.uuid4()}{os.path.splitext(file.filename)[1]}"
            filepath = os.path.join(settings.SHORTS_UPLOAD_DIR, filename)
            
            # Salvar arquivo
            async with aiofiles.open(filepath, 'wb') as f:
                content = await file.read()
                await f.write(content)
                
            return filepath
            
        except Exception as e:
            logger.error(f"Erro salvando vídeo: {e}")
            raise

    async def list_templates(self) -> List[Dict]:
        """
        Lista templates disponíveis.
        
        Returns:
            Lista de templates
        """
        # Tentar cache
        cached = await self.cache.get("templates")
        if cached:
            return cached
            
        # Carregar templates
        templates = self.config['templates']
        
        # Cachear
        await self.cache.set("templates", templates, expire=3600)
        
        return templates 

    async def download_youtube_video(self, url: str) -> str:
        """
        Baixa vídeo do YouTube.
        
        Args:
            url: URL do vídeo
            
        Returns:
            Caminho do vídeo baixado
        """
        try:
            output_path = os.path.join(
                settings.SHORTS_UPLOAD_DIR,
                f"{uuid.uuid4()}.mp4"
            )
            
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
                'outtmpl': output_path,
                'quiet': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            return output_path
            
        except Exception as e:
            logger.error(f"Erro baixando vídeo do YouTube: {e}")
            raise

    async def extract_interesting_segments(
        self,
        video_path: str,
        num_segments: int,
        segment_duration: int
    ) -> List[Dict]:
        """
        Extrai segmentos interessantes do vídeo.
        
        Args:
            video_path: Caminho do vídeo
            num_segments: Número de segmentos
            segment_duration: Duração de cada segmento
            
        Returns:
            Lista de segmentos com timestamps
        """
        try:
            video = VideoFileClip(video_path)
            
            # Calcular métricas de interesse
            segments = []
            frame_scores = []
            
            # Amostrar frames a cada segundo
            for t in range(int(video.duration)):
                frame = video.get_frame(t)
                
                # Calcular métricas
                movement = np.mean(np.abs(np.diff(frame)))
                brightness = np.mean(frame)
                contrast = np.std(frame)
                
                # Score combinado
                score = movement * 0.5 + brightness * 0.3 + contrast * 0.2
                frame_scores.append((t, score))
            
            # Ordenar por score
            frame_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Selecionar top N segmentos não sobrepostos
            used_ranges = []
            for t, _ in frame_scores:
                # Verificar se timestamp já está em algum segmento
                overlap = False
                for start, end in used_ranges:
                    if start <= t <= end:
                        overlap = True
                        break
                        
                if not overlap and len(segments) < num_segments:
                    start_time = max(0, t - segment_duration/2)
                    end_time = min(video.duration, t + segment_duration/2)
                    
                    segments.append({
                        'start': start_time,
                        'end': end_time,
                        'duration': end_time - start_time
                    })
                    
                    used_ranges.append((start_time, end_time))
                    
                if len(segments) >= num_segments:
                    break
            
            video.close()
            return segments
            
        except Exception as e:
            logger.error(f"Erro extraindo segmentos: {e}")
            raise

    async def start_video_to_shorts(
        self,
        video_url: Optional[str] = None,
        video_path: Optional[str] = None,
        duration: int = 60,
        num_shorts: int = 3,
        style: str = "cinematic",
        music_prompt: Optional[str] = None,
        voice_id: Optional[str] = None,
        hashtags: Optional[List[str]] = None,
        watermark: Optional[str] = None,
        options: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Inicia geração de shorts a partir de vídeo.
        
        Args:
            video_url: URL do vídeo do YouTube
            video_path: Caminho do vídeo local
            duration: Duração máxima de cada short
            num_shorts: Número de shorts a gerar
            style: Estilo visual
            music_prompt: Prompt para música
            voice_id: ID da voz
            hashtags: Lista de hashtags
            watermark: Texto da marca d'água
            options: Opções avançadas
            user_id: ID do usuário
            
        Returns:
            Informações da tarefa criada
        """
        task_id = str(uuid.uuid4())
        
        # Criar tarefa
        task = {
            'task_id': task_id,
            'type': 'video_to_shorts',
            'status': 'queued',
            'created_at': datetime.now().isoformat(),
            'user_id': user_id,
            'params': {
                'video_url': video_url,
                'video_path': video_path,
                'duration': duration,
                'num_shorts': num_shorts,
                'style': style,
                'music_prompt': music_prompt,
                'voice_id': voice_id,
                'hashtags': hashtags,
                'watermark': watermark,
                'options': options
            },
            'progress': 0,
            'result': None,
            'error': None
        }
        
        self.active_tasks[task_id] = task
        return task

    async def process_video_to_shorts(self, task_id: str):
        """
        Processa geração de shorts a partir de vídeo em background.
        
        Args:
            task_id: ID da tarefa
        """
        task = self.active_tasks[task_id]
        device = None
        source_video = None
        
        try:
            # Atualizar status
            task['status'] = 'processing'
            
            # Obter GPU
            device = await gpu_manager.get_device()
            
            # Carregar modelos
            await self._load_models(device)
            
            # Extrair parâmetros
            params = task['params']
            
            # 1. Obter vídeo fonte
            if params['video_url']:
                source_video = await self.download_youtube_video(params['video_url'])
            else:
                source_video = params['video_path']
                
            task['progress'] = 20
            
            # 2. Extrair segmentos interessantes
            segments = await self.extract_interesting_segments(
                video_path=source_video,
                num_segments=params['num_shorts'],
                segment_duration=params['duration']
            )
            
            task['progress'] = 40
            
            # 3. Gerar shorts para cada segmento
            shorts = []
            for i, segment in enumerate(segments):
                # Extrair segmento
                output_segment = os.path.join(
                    settings.SHORTS_OUTPUT_DIR,
                    f"segment_{task_id}_{i}.mp4"
                )
                
                await self.video_processor.extract_segment(
                    video_path=source_video,
                    output_path=output_segment,
                    start_time=segment['start'],
                    end_time=segment['end']
                )
                
                # Gerar música se solicitado
                audio_path = None
                if params['music_prompt']:
                    audio = await self.music_model.generate(
                        prompt=params['music_prompt'],
                        duration=segment['duration']
                    )
                    audio_path = os.path.join(
                        settings.SHORTS_OUTPUT_DIR,
                        f"music_{task_id}_{i}.wav"
                    )
                    await self.video_processor.save_audio(audio, audio_path)
                
                # Gerar narração se solicitado
                voice_path = None
                if params['voice_id']:
                    voice = await self.voice_model.generate(
                        text=f"Parte {i+1} do vídeo",
                        voice_id=params['voice_id']
                    )
                    voice_path = os.path.join(
                        settings.SHORTS_OUTPUT_DIR,
                        f"voice_{task_id}_{i}.wav"
                    )
                    await self.video_processor.save_audio(voice, voice_path)
                
                # Compor short final
                output_path = os.path.join(
                    settings.SHORTS_OUTPUT_DIR,
                    f"short_{task_id}_{i}.mp4"
                )
                
                # Aplicar template
                await self.video_engine.apply_template(
                    video_path=output_segment,
                    output_path=output_path,
                    template=self.config['templates']['default'],
                    params={
                        'title': f"Parte {i+1}",
                        'hashtags': params['hashtags'],
                        'watermark': params['watermark'],
                        'background_music': audio_path,
                        'voice': voice_path
                    }
                )
                
                # Gerar preview
                preview_path = os.path.join(
                    settings.SHORTS_OUTPUT_DIR,
                    f"preview_{task_id}_{i}.gif"
                )
                await self.video_processor.create_preview(
                    video_path=output_path,
                    output_path=preview_path,
                    duration=3.0
                )
                
                shorts.append({
                    'video_url': f"/media/shorts/short_{task_id}_{i}.mp4",
                    'preview_url': f"/media/shorts/preview_{task_id}_{i}.gif",
                    'duration': segment['duration'],
                    'segment': segment
                })
                
                task['progress'] = 40 + (i + 1) * 60 // len(segments)
            
            # Atualizar tarefa
            task['status'] = 'completed'
            task['progress'] = 100
            task['result'] = {
                'shorts': shorts,
                'source_video': source_video,
                'num_shorts': len(shorts)
            }
            
        except Exception as e:
            logger.error(f"Erro na geração de shorts: {e}")
            task['status'] = 'failed'
            task['error'] = str(e)
            
        finally:
            # Liberar GPU
            if device:
                await gpu_manager.release_device(device) 