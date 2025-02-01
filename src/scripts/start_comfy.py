"""
Script para iniciar o ComfyUI com as configurações apropriadas para integração com nossa API.
"""

import sys
import os
from pathlib import Path
import torch
import logging

logger = logging.getLogger(__name__)

def start_comfy():
    """Inicia o servidor ComfyUI com as configurações apropriadas"""
    base_path = Path(__file__).parent.parent.parent
    comfy_path = base_path / "ComfyUI"
    
    # Configurar variáveis de ambiente
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"
    os.environ["COMFY_MODEL_PATH"] = str(base_path / "models")
    
    # Verificar GPU
    if not torch.cuda.is_available():
        logger.warning("⚠️ AVISO: GPU não encontrada!")
    else:
        logger.info(f"✅ GPU disponível: {torch.cuda.get_device_name(0)}")
        logger.info(f"VRAM Total: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f}GB")
    
    # Adicionar ComfyUI ao path
    sys.path.append(str(comfy_path))
    
    try:
        from main import start_server
        
        # Iniciar ComfyUI
        logger.info("🚀 Iniciando servidor ComfyUI...")
        start_server(
            server_args=[
                "--listen", "0.0.0.0",  # Permite acesso externo
                "--port", "8188",       # Porta padrão
                "--enable-cors",        # Habilita CORS
                "--max-queue-size", "1",# Evita sobrecarga
                "--gpu-only"           # Usa apenas GPU
            ]
        )
    except ImportError:
        logger.error("❌ Erro ao importar ComfyUI. Verifique se está instalado corretamente.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar ComfyUI: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    start_comfy() 