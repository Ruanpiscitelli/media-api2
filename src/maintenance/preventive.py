"""
Sistema de manutenção preventiva que gerencia tarefas periódicas.
Responsável por manter a saúde e performance do sistema.
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncio
import os
import shutil

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from prometheus_client import Counter, Gauge

from src.core.config import settings
from src.core.cache.manager import cache_manager
from src.core.gpu.manager import GPUManager
from src.monitoring.alert_system import AlertSystem

# Configuração de logging
logger = logging.getLogger(__name__)

# Métricas
MAINTENANCE_RUNS = Counter(
    'maintenance_runs_total',
    'Total de execuções de manutenção',
    ['type']
)
MAINTENANCE_ERRORS = Counter(
    'maintenance_errors_total',
    'Total de erros em manutenção',
    ['type']
)
MAINTENANCE_DURATION = Gauge(
    'maintenance_duration_seconds',
    'Duração das tarefas de manutenção',
    ['type']
)

class PreventiveMaintenance:
    """
    Sistema de manutenção preventiva.
    """
    
    def __init__(
        self,
        gpu_manager: GPUManager,
        alert_system: AlertSystem
    ):
        """
        Inicializa o sistema de manutenção.
        
        Args:
            gpu_manager: Gerenciador de GPUs
            alert_system: Sistema de alertas
        """
        self.gpu_manager = gpu_manager
        self.alert_system = alert_system
        self.scheduler = AsyncIOScheduler()
        
        # Cache Redis
        self.cache = cache_manager.get_cache('maintenance')
        
        # Estado do sistema
        self._is_running = False
        self._current_task: Optional[str] = None
        
        # Configurações
        self.config = {
            'cache_cleanup': {
                'max_age_hours': 24,
                'min_free_space_gb': 10
            },
            'temp_cleanup': {
                'max_age_hours': 12,
                'paths': [
                    'tmp/generations',
                    'tmp/uploads',
                    'tmp/downloads'
                ]
            },
            'health_check': {
                'interval_minutes': 5,
                'timeout_seconds': 30
            }
        }
    
    async def start(self):
        """
        Inicia o sistema de manutenção.
        """
        if self._is_running:
            return
            
        try:
            # Configura tarefas
            self._setup_tasks()
            
            # Inicia scheduler
            self.scheduler.start()
            
            self._is_running = True
            logger.info("Sistema de manutenção iniciado")
            
        except Exception as e:
            logger.error(f"Erro iniciando sistema de manutenção: {e}")
            raise
    
    async def stop(self):
        """
        Para o sistema de manutenção.
        """
        self._is_running = False
        self.scheduler.shutdown()
        logger.info("Sistema de manutenção parado")
    
    def _setup_tasks(self):
        """
        Configura tarefas de manutenção periódicas.
        """
        # Limpeza de cache diária
        self.scheduler.add_job(
            self.clean_cache,
            CronTrigger(hour=3),  # 3 AM
            id='cache_cleanup',
            name='Cache Cleanup'
        )
        
        # Limpeza de arquivos temporários
        self.scheduler.add_job(
            self.clean_temp_files,
            CronTrigger(hour='*/6'),  # A cada 6 horas
            id='temp_cleanup',
            name='Temp Files Cleanup'
        )
        
        # Verificação de saúde
        self.scheduler.add_job(
            self.health_check,
            'interval',
            minutes=self.config['health_check']['interval_minutes'],
            id='health_check',
            name='Health Check'
        )
        
        # Backup de configurações
        self.scheduler.add_job(
            self.backup_configs,
            CronTrigger(day=1),  # Primeiro dia do mês
            id='config_backup',
            name='Config Backup'
        )
        
        # Otimização de banco de dados
        self.scheduler.add_job(
            self.optimize_database,
            CronTrigger(day=1, hour=4),  # Primeiro dia do mês, 4 AM
            id='db_optimize',
            name='Database Optimization'
        )
    
    async def clean_cache(self):
        """
        Limpa caches antigos e otimiza armazenamento.
        """
        self._current_task = 'cache_cleanup'
        start_time = datetime.utcnow()
        
        try:
            MAINTENANCE_RUNS.labels(type='cache_cleanup').inc()
            
            # Limpa cache Redis
            await self._clean_redis_cache()
            
            # Limpa cache de arquivos
            await self._clean_file_cache()
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            MAINTENANCE_DURATION.labels(type='cache_cleanup').set(duration)
            
            logger.info(f"Limpeza de cache concluída em {duration:.1f}s")
            
        except Exception as e:
            MAINTENANCE_ERRORS.labels(type='cache_cleanup').inc()
            logger.error(f"Erro na limpeza de cache: {e}")
            await self._create_maintenance_alert('cache_cleanup', str(e))
            
        finally:
            self._current_task = None
    
    async def clean_temp_files(self):
        """
        Limpa arquivos temporários antigos.
        """
        self._current_task = 'temp_cleanup'
        start_time = datetime.utcnow()
        
        try:
            MAINTENANCE_RUNS.labels(type='temp_cleanup').inc()
            
            max_age = timedelta(
                hours=self.config['temp_cleanup']['max_age_hours']
            )
            
            for path in self.config['temp_cleanup']['paths']:
                await self._clean_directory(path, max_age)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            MAINTENANCE_DURATION.labels(type='temp_cleanup').set(duration)
            
            logger.info(f"Limpeza de arquivos concluída em {duration:.1f}s")
            
        except Exception as e:
            MAINTENANCE_ERRORS.labels(type='temp_cleanup').inc()
            logger.error(f"Erro na limpeza de arquivos: {e}")
            await self._create_maintenance_alert('temp_cleanup', str(e))
            
        finally:
            self._current_task = None
    
    async def health_check(self):
        """
        Verifica saúde do sistema.
        """
        self._current_task = 'health_check'
        start_time = datetime.utcnow()
        
        try:
            MAINTENANCE_RUNS.labels(type='health_check').inc()
            
            # Verifica GPUs
            gpu_status = await self._check_gpu_health()
            
            # Verifica serviços
            service_status = await self._check_service_health()
            
            # Verifica recursos
            resource_status = await self._check_resource_health()
            
            # Processa resultados
            if not all([gpu_status, service_status, resource_status]):
                await self._create_maintenance_alert(
                    'health_check',
                    "Problemas detectados na verificação de saúde"
                )
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            MAINTENANCE_DURATION.labels(type='health_check').set(duration)
            
        except Exception as e:
            MAINTENANCE_ERRORS.labels(type='health_check').inc()
            logger.error(f"Erro na verificação de saúde: {e}")
            await self._create_maintenance_alert('health_check', str(e))
            
        finally:
            self._current_task = None
    
    async def backup_configs(self):
        """
        Realiza backup das configurações.
        """
        self._current_task = 'config_backup'
        start_time = datetime.utcnow()
        
        try:
            MAINTENANCE_RUNS.labels(type='config_backup').inc()
            
            # TODO: Implementar backup de configurações
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            MAINTENANCE_DURATION.labels(type='config_backup').set(duration)
            
        except Exception as e:
            MAINTENANCE_ERRORS.labels(type='config_backup').inc()
            logger.error(f"Erro no backup de configurações: {e}")
            await self._create_maintenance_alert('config_backup', str(e))
            
        finally:
            self._current_task = None
    
    async def optimize_database(self):
        """
        Otimiza índices do banco de dados.
        """
        self._current_task = 'db_optimize'
        start_time = datetime.utcnow()
        
        try:
            MAINTENANCE_RUNS.labels(type='db_optimize').inc()
            
            # TODO: Implementar otimização de banco de dados
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            MAINTENANCE_DURATION.labels(type='db_optimize').set(duration)
            
        except Exception as e:
            MAINTENANCE_ERRORS.labels(type='db_optimize').inc()
            logger.error(f"Erro na otimização do banco: {e}")
            await self._create_maintenance_alert('db_optimize', str(e))
            
        finally:
            self._current_task = None
    
    async def _clean_redis_cache(self):
        """
        Limpa entradas antigas do Redis.
        """
        # TODO: Implementar limpeza do Redis
        pass
    
    async def _clean_file_cache(self):
        """
        Limpa cache de arquivos.
        """
        # TODO: Implementar limpeza de cache de arquivos
        pass
    
    async def _clean_directory(self, path: str, max_age: timedelta):
        """
        Limpa arquivos antigos de um diretório.
        
        Args:
            path: Caminho do diretório
            max_age: Idade máxima dos arquivos
        """
        if not os.path.exists(path):
            return
            
        now = datetime.utcnow()
        
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                
                try:
                    mtime = datetime.fromtimestamp(
                        os.path.getmtime(file_path)
                    )
                    
                    if now - mtime > max_age:
                        os.remove(file_path)
                        
                except Exception as e:
                    logger.error(f"Erro removendo arquivo {file_path}: {e}")
    
    async def _check_gpu_health(self) -> bool:
        """
        Verifica saúde das GPUs.
        
        Returns:
            True se todas as GPUs estão saudáveis
        """
        try:
            gpu_status = await self.gpu_manager.get_status()
            
            for gpu_id, status in gpu_status.items():
                if not status['healthy']:
                    logger.warning(f"GPU {gpu_id} não saudável: {status}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erro verificando GPUs: {e}")
            return False
    
    async def _check_service_health(self) -> bool:
        """
        Verifica saúde dos serviços.
        
        Returns:
            True se todos os serviços estão saudáveis
        """
        # TODO: Implementar verificação de serviços
        return True
    
    async def _check_resource_health(self) -> bool:
        """
        Verifica saúde dos recursos.
        
        Returns:
            True se recursos estão saudáveis
        """
        # TODO: Implementar verificação de recursos
        return True
    
    async def _create_maintenance_alert(self, task: str, message: str):
        """
        Cria alerta de manutenção.
        
        Args:
            task: Tarefa que gerou o alerta
            message: Mensagem do alerta
        """
        await self.alert_system.process_alert({
            'id': f"maintenance_{task}_{datetime.utcnow().timestamp()}",
            'timestamp': datetime.utcnow(),
            'severity': 'warning',
            'type': 'maintenance',
            'message': message,
            'source': 'maintenance',
            'details': {
                'task': task,
                'current_task': self._current_task
            },
            'tags': ['maintenance', task]
        }) 