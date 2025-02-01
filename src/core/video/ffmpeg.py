"""
Wrapper seguro para FFmpeg
"""
import ffmpeg
import asyncio
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class FFmpegError(Exception):
    """Erro específico do FFmpeg"""
    pass

async def run_ffmpeg(args: list, input_path: Path, output_path: Path) -> None:
    """Executa FFmpeg com tratamento de erros"""
    try:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            *args,
            str(input_path),
            str(output_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode()
            logger.error(f"FFmpeg falhou: {error_msg}")
            
            if "No such file" in error_msg:
                raise FFmpegError("Arquivo não encontrado")
            elif "Invalid data" in error_msg:
                raise FFmpegError("Arquivo corrompido ou formato inválido")
            elif "Error while decoding" in error_msg:
                raise FFmpegError("Erro decodificando arquivo")
            else:
                raise FFmpegError(f"Erro do FFmpeg: {error_msg}")
                
    except asyncio.TimeoutError:
        raise FFmpegError("Timeout executando FFmpeg")
    except Exception as e:
        raise FFmpegError(f"Erro executando FFmpeg: {e}") 