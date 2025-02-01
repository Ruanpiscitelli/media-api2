"""
Script para testar a integração do ComfyUI com nossa API.
"""

import asyncio
import logging
from pathlib import Path
import sys

# Adicionar diretório src ao path
sys.path.append(str(Path(__file__).parent.parent))

from services.comfy_service import ComfyUIService, ComfyUIError
from core.gpu.vram_optimizer import VRAMOptimizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_basic_workflow():
    """Testa um workflow básico do SDXL"""
    async with ComfyUIService() as comfy:
        # Carregar workflow básico
        try:
            workflow = await comfy.load_workflow("sdxl_base")
            logger.info("✅ Workflow carregado com sucesso")
        except ComfyUIError as e:
            logger.error(f"❌ Erro ao carregar workflow: {str(e)}")
            return
        
        # Executar workflow
        try:
            prompt_id = await comfy.execute_workflow(
                workflow,
                prompt_inputs={
                    "text": "A beautiful landscape with mountains and a lake",
                    "seed": 42,
                    "steps": 20
                }
            )
            logger.info(f"✅ Workflow enviado com ID: {prompt_id}")
            
            # Aguardar execução
            result = await comfy.wait_for_execution(prompt_id)
            logger.info("✅ Execução concluída com sucesso")
            logger.info(f"Resultado: {result}")
            
        except ComfyUIError as e:
            logger.error(f"❌ Erro na execução: {str(e)}")

async def test_vram_management():
    """Testa o gerenciamento de VRAM"""
    vram_optimizer = VRAMOptimizer()
    
    # Simular carga de trabalho
    vram_optimizer.workload_tracker["comfyui"]["test_workflow"] = {
        "nodes": {
            "1": {"class_type": "LoadCheckpoint"},
            "2": {"class_type": "KSampler"},
            "3": {"class_type": "VAEDecode"},
            "4": {"class_type": "SaveImage"}
        }
    }
    
    # Iniciar otimização
    try:
        optimization_task = asyncio.create_task(
            vram_optimizer.optimize_allocations()
        )
        
        # Aguardar alguns ciclos de otimização
        await asyncio.sleep(10)
        
        # Cancelar tarefa
        optimization_task.cancel()
        logger.info("✅ Teste de gerenciamento de VRAM concluído")
        
    except Exception as e:
        logger.error(f"❌ Erro no gerenciamento de VRAM: {str(e)}")

async def test_error_handling():
    """Testa o tratamento de erros"""
    async with ComfyUIService() as comfy:
        # Testar workflow inválido
        try:
            await comfy.execute_workflow({"invalid": "workflow"})
            logger.error("❌ Deveria ter falhado com workflow inválido")
        except ComfyUIError:
            logger.info("✅ Erro tratado corretamente para workflow inválido")
        
        # Testar interrupção
        try:
            await comfy.interrupt_execution()
            logger.info("✅ Interrupção executada com sucesso")
        except ComfyUIError as e:
            logger.error(f"❌ Erro ao interromper execução: {str(e)}")

async def main():
    """Função principal de testes"""
    logger.info("🚀 Iniciando testes de integração do ComfyUI")
    
    # Testar workflow básico
    logger.info("\n=== Testando Workflow Básico ===")
    await test_basic_workflow()
    
    # Testar gerenciamento de VRAM
    logger.info("\n=== Testando Gerenciamento de VRAM ===")
    await test_vram_management()
    
    # Testar tratamento de erros
    logger.info("\n=== Testando Tratamento de Erros ===")
    await test_error_handling()
    
    logger.info("\n✨ Testes concluídos")

if __name__ == "__main__":
    asyncio.run(main()) 