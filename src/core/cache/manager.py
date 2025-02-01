"""
Sistema de cache unificado com suporte a Redis e memória local.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta
import aioredis
from prometheus_client import Counter, Gauge
from prometheus_client.registry import REGISTRY

from src.core.config import settings
from src.core.errors import APIError
from src.core.monitoring.metrics import CACHE_METRICS

logger = logging.getLogger(__name__)

# Verificar se as métricas já existem antes de criar
def create_metrics():
    """Cria métricas Prometheus se não existirem"""
    metrics = {}
    
    # Cache Hits
    try:
        metrics['cache_hits'] = REGISTRY.get_sample_value('cache_hits_total')
    except:
        metrics['cache_hits'] = Counter(
            'cache_hits_total',
            'Total de hits no cache',
            ['type']
        )
    
    # Cache Misses
    try:
        metrics['cache_misses'] = REGISTRY.get_sample_value('cache_misses_total')
    except:
        metrics['cache_misses'] = Counter(
            'cache_misses_total',
            'Total de misses no cache',
            ['type']
        )
    
    # Cache Size
    try:
        metrics['cache_size'] = REGISTRY.get_sample_value('cache_size_bytes')
    except:
        metrics['cache_size'] = Gauge(
            'cache_size_bytes',
            'Tamanho do cache em bytes',
            ['type']
        )
    
    return metrics

# Criar métricas
METRICS = create_metrics()
CACHE_HITS = METRICS['cache_hits']
CACHE_MISSES = METRICS['cache_misses']
CACHE_SIZE = METRICS['cache_size']

class CacheError(APIError):
    """Erro base para problemas com cache"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            status_code=503,
            error_code="cache_error",
            details=details
        )

class CacheManager:
    """
    Gerenciador de cache unificado.
    Suporta Redis e cache local com fallback automático.
    """
    def __init__(self):
        self.redis = None
        self.local_cache = {}
        self.metrics = CACHE_METRICS
        self.local_lock = asyncio.Lock()
        self._connect()

    def _connect(self):
        """Estabelece conexão com Redis de forma assíncrona"""
        try:
            self.redis = await aioredis.from_url(
                str(settings.REDIS_URL),
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_TIMEOUT
            )
            logger.info("✅ Conexão Redis estabelecida com sucesso")
        except Exception as e:
            logger.warning(f"❌ Erro ao conectar ao Redis: {e}")
            self.redis = None
            
    async def ensure_connection(self):
        """Garante que existe uma conexão Redis"""
        if self.redis is None:
            await self._connect()

    async def get_cache(self, namespace: str) -> 'Cache':
        """Retorna uma interface de cache para o namespace especificado"""
        await self.ensure_connection()
        return Cache(namespace, self)

    async def get(self, namespace: str, key: str) -> Optional[Any]:
        """Obtém valor do cache"""
        try:
            if self.redis:
                # Tentar Redis primeiro
                value = await self.redis.get(f"{namespace}:{key}")
                if value:
                    CACHE_HITS.labels(type="redis").inc()
                    return json.loads(value)
            
            # Fallback para cache local
            async with self.local_lock:
                if namespace in self.local_cache and key in self.local_cache[namespace]:
                    CACHE_HITS.labels(type="local").inc()
                    return self.local_cache[namespace][key]
                    
            CACHE_MISSES.labels(type="all").inc()
            return None
            
        except Exception as e:
            logger.error(f"Erro ao obter do cache: {e}")
            return None

    async def set(
        self, 
        namespace: str, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Define valor no cache"""
        try:
            json_value = json.dumps(value)
            
            if self.redis:
                # Tentar Redis primeiro
                await self.redis.set(
                    f"{namespace}:{key}",
                    json_value,
                    ex=ttl
                )
            
            # Backup em cache local
            async with self.local_lock:
                if namespace not in self.local_cache:
                    self.local_cache[namespace] = {}
                self.local_cache[namespace][key] = value
                
            return True
            
        except Exception as e:
            logger.error(f"Erro ao definir no cache: {e}")
            return False

    async def delete(self, namespace: str, key: str) -> bool:
        """Remove valor do cache"""
        try:
            if self.redis:
                await self.redis.delete(f"{namespace}:{key}")
                
            async with self.local_lock:
                if namespace in self.local_cache:
                    self.local_cache[namespace].pop(key, None)
                    
            return True
            
        except Exception as e:
            logger.error(f"Erro ao deletar do cache: {e}")
            return False

    async def clear(self, namespace: str = None) -> bool:
        """Limpa todo o cache ou apenas um namespace"""
        try:
            if namespace:
                if self.redis:
                    keys = await self.redis.keys(f"{namespace}:*")
                    if keys:
                        await self.redis.delete(*keys)
                        
                async with self.local_lock:
                    self.local_cache.pop(namespace, None)
            else:
                if self.redis:
                    await self.redis.flushdb()
                    
                async with self.local_lock:
                    self.local_cache.clear()
                    
            return True
            
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
            return False

class Cache:
    """Interface de cache para um namespace específico"""
    
    def __init__(self, namespace: str, manager: CacheManager):
        self.namespace = namespace
        self.manager = manager
        
    async def get(self, key: str) -> Optional[Any]:
        return await self.manager.get(self.namespace, key)
        
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        return await self.manager.set(self.namespace, key, value, ttl)
        
    async def delete(self, key: str) -> bool:
        return await self.manager.delete(self.namespace, key)
        
    async def clear(self) -> bool:
        return await self.manager.clear(self.namespace)

# Instância global do gerenciador de cache
cache_manager = CacheManager()

# Garantir que Cache está disponível para importação
__all__ = ['CacheManager', 'CacheError', 'cache_manager', 'Cache'] 