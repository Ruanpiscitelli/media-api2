"""
Script para verificar a presença e integridade dos modelos
"""
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_comfy_models():
    """Verifica os modelos do ComfyUI"""
    COMFY_DIR = Path("/workspace/ComfyUI")
    MODELS_DIR = COMFY_DIR / "models"
    
    # Lista de modelos esperados
    expected_models = {
        "checkpoints": [
            "sd_xl_base_1.0.safetensors",
            "sd_xl_refiner_1.0.safetensors"
        ],
        "vae": [
            "sdxl_vae.safetensors"
        ]
    }
    
    all_ok = True
    
    # Verificar cada tipo de modelo
    for model_type, models in expected_models.items():
        type_dir = MODELS_DIR / model_type
        logger.info(f"\nVerificando diretório {type_dir}:")
        
        if not type_dir.exists():
            logger.error(f"❌ Diretório {model_type} não encontrado")
            all_ok = False
            continue
            
        # Verificar cada modelo
        for model in models:
            model_path = type_dir / model
            if model_path.exists():
                size_mb = model_path.stat().st_size / (1024 * 1024)
                logger.info(f"✅ {model} encontrado ({size_mb:.1f}MB)")
            else:
                logger.error(f"❌ {model} não encontrado")
                all_ok = False
    
    # Verificar estrutura de diretórios
    expected_dirs = [
        "checkpoints", "clip", "clip_vision", "controlnet",
        "ipadapter", "loras", "upscale_models", "vae"
    ]
    
    logger.info("\nVerificando estrutura de diretórios:")
    for dir_name in expected_dirs:
        dir_path = MODELS_DIR / dir_name
        if dir_path.exists():
            logger.info(f"✅ Diretório {dir_name} existe")
        else:
            logger.error(f"❌ Diretório {dir_name} não encontrado")
            all_ok = False
    
    return all_ok

if __name__ == "__main__":
    logger.info("Iniciando verificação dos modelos...")
    
    if check_comfy_models():
        logger.info("\n✅ Todos os modelos e diretórios verificados com sucesso!")
    else:
        logger.error("\n❌ Alguns modelos ou diretórios estão faltando") 