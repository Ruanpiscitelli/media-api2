"""
Serviço para gerenciamento de thumbnails com suporte a cache.
"""

import os
from typing import Optional, Tuple
from pathlib import Path
import asyncio

from src.core.cache.manager import cache_manager
from src.generation.video.ffmpeg.thumbnail import ThumbnailGenerator
import torch

class ThumbnailService:
    """
    Serviço para gerenciamento de thumbnails de vídeo.
    Implementa cache e otimizações para evitar regeneração desnecessária.
    """
    
    def __init__(self):
        """Inicializa o serviço de thumbnails."""
        self.generator = ThumbnailGenerator()
        self.cache_ttl = 3600 * 24  # 24 horas
        
    async def get_or_generate(
        self,
        video_path: str,
        animated: bool = True,
        **kwargs
    ) -> Tuple[str, bool]:
        """
        Obtém ou gera um thumbnail para o vídeo.
        Verifica primeiro no cache antes de gerar um novo.
        
        Args:
            video_path: Caminho do vídeo fonte
            animated: Se True, gera GIF animado. Se False, gera imagem estática
            **kwargs: Argumentos adicionais para o gerador
            
        Returns:
            Tuple[str, bool]: (caminho do thumbnail, True se foi gerado agora)
        """
        video_id = Path(video_path).stem
        cache_key = f"thumbnail:{video_id}:{'animated' if animated else 'static'}"
        
        # Tenta obter do cache
        cached_path = await cache_manager.get(cache_key)
        if cached_path and os.path.exists(cached_path):
            return cached_path, False
            
        # Gera novo thumbnail
        if animated:
            thumbnail_path = await self.generator.generate_animated(
                video_path,
                **kwargs
            )
        else:
            thumbnail_path = await self.generator.generate_static(
                video_path,
                **kwargs
            )
            
        # Salva no cache
        await cache_manager.set(
            cache_key,
            thumbnail_path,
            ttl=self.cache_ttl
        )
        
        return thumbnail_path, True
        
    async def clear_cache(self, video_id: str) -> None:
        """
        Limpa o cache de thumbnails para um vídeo específico.
        
        Args:
            video_id: ID do vídeo
        """
        keys = [
            f"thumbnail:{video_id}:animated",
            f"thumbnail:{video_id}:static"
        ]
        
        for key in keys:
            cached_path = await cache_manager.get(key)
            if cached_path and os.path.exists(cached_path):
                os.remove(cached_path)
            await cache_manager.delete(key)
            
    async def generate_thumbnail(self, video_path: Path) -> bytes:
        """
        Gera um thumbnail estático de um vídeo usando ffmpeg.
        
        Args:
            video_path: Caminho do arquivo de vídeo
            
        Returns:
            bytes: Dados binários da imagem thumbnail
        """
        args = [
            "ffmpeg",
            "-i", str(video_path.resolve()),
            "-ss", "00:00:01",
            "-vframes", "1",
            "-f", "image2pipe",
            "-"
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError(f"Erro ao gerar thumbnail: {stderr.decode()}")
            
        return stdout

# Instância global do serviço
thumbnail_service = ThumbnailService() 