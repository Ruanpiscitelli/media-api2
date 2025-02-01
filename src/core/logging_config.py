"""
Configuração unificada de logging com suporte a métricas GPU e formatação personalizada.
"""

import logging
import logging.config
from typing import Dict, Any
from prometheus_client import Counter

from src.core.gpu.manager import gpu_manager

# Métricas
LOG_COUNTS = Counter('log_count_total', 'Total de logs por nível', ['level'])

class GPULogFilter(logging.Filter):
    """Adiciona estatísticas de GPU aos logs"""
    def filter(self, record):
        try:
            record.gpu_stats = gpu_manager.get_status()
        except:
            record.gpu_stats = {}
        return True

class MetricsHandler(logging.Handler):
    """Handler que incrementa métricas Prometheus"""
    def emit(self, record):
        LOG_COUNTS.labels(record.levelname.lower()).inc()

class CustomFormatter(logging.Formatter):
    """Formatador com cores e informações de GPU"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[41m',  # Red background
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Adiciona cor ao nível de log
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname_colored = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        else:
            record.levelname_colored = levelname
            
        # Formata estatísticas de GPU se disponíveis
        if hasattr(record, 'gpu_stats'):
            gpu_info = []
            for gpu in record.gpu_stats:
                if isinstance(gpu, dict):
                    util = gpu.get('utilization', 0)
                    mem = gpu.get('memory', {})
                    used_gb = mem.get('used', 0) / (1024**3)
                    total_gb = mem.get('total', 0) / (1024**3)
                    gpu_info.append(
                        f"GPU{gpu.get('id', '?')}: {util}% {used_gb:.1f}/{total_gb:.1f}GB"
                    )
            record.gpu_stats_formatted = ' | '.join(gpu_info)
        else:
            record.gpu_stats_formatted = ''
            
        return super().format(record)

def setup_logging(config: Dict[str, Any] = None) -> None:
    """
    Configura logging com handlers personalizados e métricas.
    
    Args:
        config: Configuração opcional de logging
    """
    if config is None:
        config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'detailed': {
                    '()': CustomFormatter,
                    'format': '%(asctime)s [%(levelname_colored)s] %(name)s: %(message)s %(gpu_stats_formatted)s'
                },
                'simple': {
                    'format': '%(levelname)s %(message)s'
                }
            },
            'filters': {
                'gpu_stats': {
                    '()': GPULogFilter
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'detailed',
                    'filters': ['gpu_stats']
                },
                'file': {
                    'class': 'logging.FileHandler',
                    'filename': 'app.log',
                    'formatter': 'detailed',
                    'filters': ['gpu_stats']
                },
                'metrics': {
                    '()': MetricsHandler
                }
            },
            'root': {
                'level': 'INFO',
                'handlers': ['console', 'file', 'metrics']
            },
            'loggers': {
                'src': {
                    'level': 'DEBUG',
                    'handlers': ['console', 'file', 'metrics'],
                    'propagate': False
                }
            }
        }
    
    logging.config.dictConfig(config)
    
    # Configura logging para bibliotecas terceiras
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('fastapi').setLevel(logging.INFO)
    logging.getLogger('celery').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info('Logging configurado com sucesso') 