"""
Configuração do sistema de gerenciamento de GPUs.
Otimizado para setup com 4x RTX 4090.
"""

from typing import Dict, List

# Configuração base das GPUs
GPU_CONFIG = {
    # IDs das GPUs disponíveis (0-3 para 4 GPUs)
    'devices': [0, 1, 2, 3],
    
    # Fração máxima de memória a ser usada por GPU (90%)
    'memory_fraction': 0.9,
    
    # Tamanhos de batch otimizados por tipo de tarefa
    'batch_sizes': {
        'sdxl': 4,        # Geração de imagens com SDXL
        'fish_speech': 8,  # Síntese de voz
        'video': 2        # Geração de vídeo
    },
    
    # Prioridades de GPU por tipo de tarefa
    'priorities': {
        'image': [0, 1],    # GPUs 0 e 1 prioritárias para imagens
        'speech': [2],      # GPU 2 prioritária para áudio
        'video': [3]        # GPU 3 prioritária para vídeo
    },
    
    # Limites de memória por tipo de tarefa (em MB)
    'memory_limits': {
        'image': 12000,    # 12GB para geração de imagens
        'speech': 8000,    # 8GB para síntese de voz
        'video': 16000     # 16GB para geração de vídeo
    },
    
    # Configurações de otimização
    'optimization': {
        'enable_tf32': True,           # Habilitar TF32 para melhor performance
        'enable_cuda_graphs': True,    # Usar CUDA Graphs para tarefas repetitivas
        'enable_cudnn_benchmarks': True,  # Habilitar benchmarks do cuDNN
        'enable_memory_efficient_attention': True,  # Usar atenção eficiente em memória
        'compile_mode': 'reduce-overhead'  # Modo de compilação para torch.compile
    },
    
    # Configurações de fallback e recuperação
    'fallback': {
        'max_retries': 3,              # Número máximo de tentativas em caso de erro
        'retry_delay': 5,              # Delay entre tentativas (segundos)
        'enable_error_recovery': True,  # Habilitar recuperação automática de erros
        'memory_headroom': 1024        # Espaço livre mínimo em MB
    },
    
    # Configurações de monitoramento
    'monitoring': {
        'metrics_interval': 5,         # Intervalo de coleta de métricas (segundos)
        'temperature_limit': 85,       # Limite de temperatura em Celsius
        'utilization_threshold': 95,   # Limite de utilização em %
        'memory_threshold': 95         # Limite de uso de memória em %
    },
    
    # Configurações específicas por modelo
    'model_configs': {
        'sdxl': {
            'precision': 'float16',
            'attention_slicing': True,
            'vae_slicing': True,
            'enable_xformers': True
        },
        'fish_speech': {
            'precision': 'float16',
            'batch_processing': True,
            'stream_buffer_size': 8192
        },
        'video': {
            'precision': 'float32',  # Maior precisão para vídeo
            'frame_buffer_size': 32,
            'enable_nvdec': True     # Usar decodificação por hardware
        }
    }
}

# Configurações de pipeline
PIPELINE_CONFIG = {
    'max_concurrent_tasks': 8,     # Máximo de tarefas simultâneas
    'queue_size': 100,            # Tamanho máximo da fila
    'priority_levels': {
        'realtime': 0,            # Prioridade máxima
        'high': 1,
        'normal': 2,
        'batch': 3                # Prioridade mínima
    }
}

# Configurações de cache
CACHE_CONFIG = {
    'vram_cache_size': 4096,      # Tamanho do cache em VRAM (MB)
    'system_ram_cache_size': 16384,  # Tamanho do cache em RAM (MB)
    'cache_ttl': 3600,            # Tempo de vida do cache (segundos)
    'enable_persistent_cache': True  # Habilitar cache persistente
}

def get_gpu_config() -> Dict:
    """
    Retorna a configuração completa das GPUs.
    """
    return GPU_CONFIG

def get_pipeline_config() -> Dict:
    """
    Retorna a configuração do pipeline de processamento.
    """
    return PIPELINE_CONFIG

def get_cache_config() -> Dict:
    """
    Retorna a configuração do sistema de cache.
    """
    return CACHE_CONFIG

def get_device_map() -> Dict[str, List[int]]:
    """
    Retorna o mapeamento de tipos de tarefa para GPUs.
    """
    return {
        task: devices
        for task, devices in GPU_CONFIG['priorities'].items()
    } 