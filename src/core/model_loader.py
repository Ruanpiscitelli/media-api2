"""
Carregamento de modelos com gerenciamento de memória
"""
import torch
from pathlib import Path
import gc

class ModelLoader:
    def __init__(self):
        self.loaded_models = {}
        
    async def load_model(self, model_path: Path, device: str = "cuda"):
        """Carrega modelo com verificação de memória"""
        try:
            # Limpar memória antes de carregar
            torch.cuda.empty_cache()
            gc.collect()
            
            # Verificar memória disponível
            if torch.cuda.is_available():
                free_mem = torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated()
                if free_mem < 8 * 1024 * 1024 * 1024:  # 8GB
                    raise RuntimeError("Memória GPU insuficiente")
                    
            # Carregar modelo
            model = torch.load(model_path)
            self.loaded_models[str(model_path)] = model
            return model
            
        except Exception as e:
            raise RuntimeError(f"Erro carregando modelo: {e}") 