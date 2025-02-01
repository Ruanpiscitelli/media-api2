"""
Script para testar a integração com o ComfyUI.
"""

import asyncio
import json
from pathlib import Path
from loguru import logger

from src.comfy.client import comfy_client
from src.comfy.server import comfy_server
from src.comfy.config import comfy_settings

async def test_comfy_integration():
    """Testa a integração com o ComfyUI"""
    try:
        # Configurar timeout para inicialização
        try:
            async with asyncio.timeout(60):
                await comfy_server.start()
        except TimeoutError:
            logger.error("Timeout na inicialização do ComfyUI")
            return
        
        # Carregar workflow de teste
        logger.info("Carregando workflow de teste...")
        workflow_path = Path("workflows/base/sdxl/base.json")
        
        async with comfy_client:
            # Carregar workflow
            workflow = await comfy_client.load_workflow_from_file(workflow_path)
            
            # Executar workflow
            logger.info("Executando workflow...")
            result = await comfy_client.execute_workflow(workflow)
            
            if result:
                logger.info("Workflow executado com sucesso!")
                logger.info(f"Resultado: {json.dumps(result, indent=2)}")
            else:
                logger.error("Timeout ao executar workflow")
                
    except Exception as e:
        logger.error(f"Erro ao testar integração: {str(e)}")
    finally:
        # Parar servidor
        logger.info("Parando servidor ComfyUI...")
        await comfy_server.stop()

if __name__ == "__main__":
    # Executar teste
    asyncio.run(test_comfy_integration()) 