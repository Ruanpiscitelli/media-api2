"""
Configuração do Celery para processamento assíncrono de tarefas.
Integra com o gerenciador de GPUs para alocação dinâmica de recursos.
"""

from celery import Celery
from celery.signals import worker_ready
from prometheus_client import Counter, Histogram

from src.core.config import settings
from src.core.gpu.manager import gpu_manager
from src.core.initialization import cache_manager
from src.core.logger import logger

# Métricas Prometheus
TASK_COUNTER = Counter(
    "celery_tasks_total",
    "Total de tarefas processadas",
    ["task_type", "status"]
)

TASK_DURATION = Histogram(
    "celery_task_duration_seconds",
    "Duração das tarefas em segundos",
    ["task_type"]
)

# Configuração do Celery
app = Celery(
    "media_generation",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configurações do worker
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hora
    worker_prefetch_multiplier=1,  # Processa uma tarefa por vez
    worker_max_tasks_per_child=100,  # Reinicia worker após 100 tarefas
)

# Configuração de filas com prioridade
app.conf.task_queues = {
    "high": {"exchange": "media", "routing_key": "high"},
    "default": {"exchange": "media", "routing_key": "default"},
    "low": {"exchange": "media", "routing_key": "low"},
}

app.conf.task_routes = {
    "src.generation.image.tasks.*": {"queue": "high"},
    "src.generation.video.tasks.*": {"queue": "default"},
    "src.generation.speech.tasks.*": {"queue": "low"},
}

@worker_ready.connect
def init_worker(sender=None, **kwargs):
    """Inicializa recursos quando o worker inicia"""
    try:
        # Inicializa monitoramento de GPU
        sender.app.control.broadcast("monitor_gpus")
        
        # Obtem ou cria um novo event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        # Executa inicialização assíncrona
        loop.run_until_complete(async_init_worker())
        logger.info("Worker inicializado com sucesso")
    except Exception as e:
        logger.error(f"Erro inicializando worker: {e}")
        raise

async def async_init_worker():
    """Função assíncrona real de inicialização"""
    await cache_manager.ensure_connection()
    await gpu_manager.initialize()

# Importa tarefas
import src.generation.image.tasks
import src.generation.video.tasks
import src.generation.speech.tasks 