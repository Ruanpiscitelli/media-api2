"""
Script para download automático dos modelos na inicialização.
"""

import asyncio
import logging
from src.models.model_manager import model_manager

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def main():
    """Função principal para download dos modelos."""
    try:
        logger.info("Iniciando download dos modelos...")
        await model_manager.setup_system()
        logger.info("Download dos modelos concluído com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro durante o download dos modelos: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 