"""
Configuração de logging.
"""
import logging.config
import sys
from src.core.config import settings

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "default",
            "level": settings.LOG_LEVEL
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "/workspace/logs/api.log",
            "formatter": "json",
            "level": settings.LOG_LEVEL
        }
    },
    "root": {
        "handlers": ["console", "file"],
        "level": settings.LOG_LEVEL
    }
}

def setup_logging():
    """Configura logging da aplicação"""
    logging.config.dictConfig(LOGGING_CONFIG) 