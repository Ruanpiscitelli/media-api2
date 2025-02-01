"""
Serviço de síntese de voz usando Fish Speech
"""
import torch
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class SpeechService:
    def __init__(self):
        self.model = None
        self.device = None
        
    async def initialize(self):
        """Inicializa modelo Fish Speech"""
        try:
            model_path = Path("/workspace/models/fish_speech/model.pt")
            if not model_path.exists():
                raise RuntimeError(
                    "Modelo Fish Speech não encontrado em: "
                    f"{model_path}"
                )
                
            # Verificar CUDA
            if not torch.cuda.is_available():
                raise RuntimeError(
                    "CUDA não disponível para Fish Speech"
                )
                
            # Verificar VRAM
            gpu = torch.cuda.get_device_properties(0)
            if gpu.total_memory < 4 * 1024 * 1024 * 1024:  # 4GB
                raise RuntimeError(
                    "GPU sem memória suficiente para Fish Speech"
                )
                
            # Carregar modelo
            self.device = torch.device("cuda")
            self.model = torch.load(model_path).to(self.device)
            
        except Exception as e:
            logger.error(f"Erro inicializando Fish Speech: {e}")
            raise 