"""
Sistema central de logs que integra Elasticsearch, Logstash e Kibana.
Responsável por coletar, processar e visualizar logs de todo o sistema.
"""

import logging
import logging.config
from typing import Dict, Optional
from datetime import datetime
import json
import os

from elasticsearch import AsyncElasticsearch
from pythonjsonlogger import jsonlogger

from src.core.config import settings

# Configuração de logging
logger = logging.getLogger(__name__)

class LogSystem:
    """
    Sistema central de logs que integra ELK Stack.
    """
    
    def __init__(self):
        """
        Inicializa o sistema de logs.
        """
        self.es_client = AsyncElasticsearch(
            hosts=settings.ELASTICSEARCH_HOSTS,
            basic_auth=(
                settings.ELASTICSEARCH_USER,
                settings.ELASTICSEARCH_PASSWORD
            )
        )
        
        # Configuração de índices
        self.indices = {
            'application': 'media-api-logs',
            'access': 'media-api-access',
            'error': 'media-api-errors',
            'audit': 'media-api-audit'
        }
        
        # Configuração de retenção (em dias)
        self.retention = {
            'application': 30,
            'access': 90,
            'error': 180,
            'audit': 365
        }
    
    async def setup(self):
        """
        Configura o sistema de logs.
        """
        try:
            # Configura formato JSON para logs
            logging.config.dictConfig({
                'version': 1,
                'disable_existing_loggers': False,
                'formatters': {
                    'json': {
                        '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                        'fmt': '%(asctime)s %(name)s %(levelname)s %(message)s'
                    }
                },
                'handlers': {
                    'elastic': {
                        'class': 'src.monitoring.handlers.AsyncElasticsearchHandler',
                        'formatter': 'json',
                        'es_client': self.es_client,
                        'index': self.indices['application']
                    },
                    'console': {
                        'class': 'logging.StreamHandler',
                        'formatter': 'json',
                        'stream': 'ext://sys.stdout'
                    },
                    'error_file': {
                        'class': 'logging.handlers.RotatingFileHandler',
                        'formatter': 'json',
                        'filename': 'logs/error.log',
                        'maxBytes': 10485760,  # 10MB
                        'backupCount': 10
                    }
                },
                'loggers': {
                    '': {  # Root logger
                        'handlers': ['elastic', 'console'],
                        'level': 'INFO'
                    },
                    'src': {  # App logger
                        'handlers': ['elastic', 'console', 'error_file'],
                        'level': 'INFO',
                        'propagate': False
                    }
                }
            })
            
            # Cria índices se não existirem
            await self._setup_indices()
            
            # Configura políticas de retenção
            await self._setup_retention_policies()
            
            logger.info("Sistema de logs configurado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro configurando sistema de logs: {e}")
            raise
    
    async def _setup_indices(self):
        """
        Cria e configura índices do Elasticsearch.
        """
        for index_name in self.indices.values():
            if not await self.es_client.indices.exists(index=index_name):
                await self.es_client.indices.create(
                    index=index_name,
                    body={
                        'settings': {
                            'number_of_shards': 3,
                            'number_of_replicas': 1
                        },
                        'mappings': {
                            'properties': {
                                '@timestamp': {'type': 'date'},
                                'level': {'type': 'keyword'},
                                'logger': {'type': 'keyword'},
                                'message': {'type': 'text'},
                                'exception': {'type': 'text'},
                                'trace_id': {'type': 'keyword'},
                                'user_id': {'type': 'keyword'},
                                'ip': {'type': 'ip'},
                                'path': {'type': 'keyword'},
                                'method': {'type': 'keyword'},
                                'status_code': {'type': 'integer'},
                                'response_time': {'type': 'float'},
                                'user_agent': {'type': 'keyword'}
                            }
                        }
                    }
                )
    
    async def _setup_retention_policies(self):
        """
        Configura políticas de retenção dos índices.
        """
        for index_type, days in self.retention.items():
            policy_name = f"{index_type}-retention"
            
            await self.es_client.ilm.put_lifecycle(
                name=policy_name,
                body={
                    'policy': {
                        'phases': {
                            'hot': {
                                'min_age': '0ms',
                                'actions': {
                                    'rollover': {
                                        'max_age': '1d',
                                        'max_size': '50gb'
                                    }
                                }
                            },
                            'delete': {
                                'min_age': f"{days}d",
                                'actions': {
                                    'delete': {}
                                }
                            }
                        }
                    }
                }
            )
    
    async def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time: float,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Registra log de requisição HTTP.
        """
        document = {
            '@timestamp': datetime.utcnow().isoformat(),
            'type': 'access',
            'method': method,
            'path': path,
            'status_code': status_code,
            'response_time': response_time,
            'user_id': user_id,
            'ip': ip,
            'user_agent': user_agent
        }
        
        await self.es_client.index(
            index=self.indices['access'],
            document=document
        )
    
    async def log_error(
        self,
        error: Exception,
        context: Dict,
        trace_id: Optional[str] = None
    ):
        """
        Registra log de erro com contexto.
        """
        document = {
            '@timestamp': datetime.utcnow().isoformat(),
            'type': 'error',
            'error_type': error.__class__.__name__,
            'error_message': str(error),
            'traceback': self._format_traceback(error),
            'context': context,
            'trace_id': trace_id
        }
        
        await self.es_client.index(
            index=self.indices['error'],
            document=document
        )
    
    async def log_audit(
        self,
        action: str,
        user_id: str,
        resource: str,
        changes: Dict,
        ip: Optional[str] = None
    ):
        """
        Registra log de auditoria.
        """
        document = {
            '@timestamp': datetime.utcnow().isoformat(),
            'type': 'audit',
            'action': action,
            'user_id': user_id,
            'resource': resource,
            'changes': changes,
            'ip': ip
        }
        
        await self.es_client.index(
            index=self.indices['audit'],
            document=document
        )
    
    def _format_traceback(self, error: Exception) -> str:
        """
        Formata traceback de erro.
        """
        import traceback
        return ''.join(traceback.format_exception(
            type(error),
            error,
            error.__traceback__
        )) 