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
import time

from src.core.config import settings
from src.core.errors import APIError

logger = logging.getLogger(__name__)

# Métricas
CACHE_HITS = Counter('cache_hits_total', 'Total de hits no cache', ['type'])
CACHE_MISSES = Counter('cache_misses_total', 'Total de misses no cache', ['type'])
CACHE_SIZE = Gauge('cache_size_bytes', 'Tamanho do cache em bytes', ['type'])

class CacheError(APIError):
    """Erro base para problemas com cache"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            status_code=503,
            error_code="cache_error",
            details=details
        )

class Cache:
    """
    Cache unificado com fallback local.
    
    Features:
    - Cache em memória com LRU
    - Cache distribuído com Redis
    - Fallback automático
    - Métricas Prometheus
    - Serialização JSON
    - TTL configurável
    - Compressão opcional
    """
    
    def __init__(self):
        """Inicializa conexões e estruturas de dados"""
        self.local_cache: Dict[str, Dict[str, Any]] = {}
        self.local_lock = asyncio.Lock()
        self.redis: Optional[aioredis.Redis] = None
        self._connect_redis()
        self._cache: Dict[str, Any] = {}
        self._expires: Dict[str, float] = {}
        
    def _connect_redis(self):
        """Estabelece conexão com Redis"""
        try:
            self.redis = aioredis.from_url(
                f"redis://{settings.cache.redis.host}:{settings.cache.redis.port}",
                password=settings.cache.redis.password,
                db=settings.cache.redis.db,
                ssl=settings.cache.redis.ssl,
                socket_timeout=settings.cache.redis.socket_timeout,
                retry_on_timeout=settings.cache.redis.retry_on_timeout,
                max_connections=settings.cache.redis.max_connections
            )
        except Exception as e:
            logger.warning(f"Erro ao conectar ao Redis: {e}")
            self.redis = None
            
    async def get(
        self,
        key: str,
        default: Any = None,
        use_local: bool = True
    ) -> Any:
        """
        Obtém valor do cache.
        
        Args:
            key: Chave do cache
            default: Valor padrão se não encontrado
            use_local: Se deve usar cache local
            
        Returns:
            Valor armazenado ou default
        """
        # Tenta Redis primeiro
        if self.redis:
            try:
                value = await self.redis.get(key)
                if value:
                    CACHE_HITS.labels('redis').inc()
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Erro ao ler do Redis: {e}")
                
        # Fallback para cache local
        if use_local:
            async with self.local_lock:
                if key in self.local_cache:
                    entry = self.local_cache[key]
                    if not self._is_expired(entry):
                        CACHE_HITS.labels('local').inc()
                        return entry['value']
                    else:
                        del self.local_cache[key]
                        
        CACHE_MISSES.labels('all').inc()
        return default
        
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        use_local: bool = True
    ) -> None:
        """
        Armazena valor no cache.
        
        Args:
            key: Chave do cache
            value: Valor a armazenar
            ttl: Tempo de vida em segundos
            use_local: Se deve usar cache local
        """
        if ttl is None:
            ttl = settings.cache.ttl
            
        # Serializa valor
        json_value = json.dumps(value)
        
        # Tenta Redis primeiro
        if self.redis:
            try:
                await self.redis.set(key, json_value, ex=ttl)
                CACHE_SIZE.labels('redis').inc(len(json_value))
            except Exception as e:
                logger.warning(f"Erro ao escrever no Redis: {e}")
                
        # Fallback para cache local
        if use_local:
            async with self.local_lock:
                # Limpa cache se necessário
                if len(self.local_cache) >= settings.cache.max_size:
                    self._cleanup_local_cache()
                    
                self.local_cache[key] = {
                    'value': value,
                    'expires_at': datetime.now() + timedelta(seconds=ttl)
                }
                CACHE_SIZE.labels('local').inc(len(json_value))
                
    async def delete(self, key: str) -> None:
        """Remove chave do cache"""
        if self.redis:
            try:
                await self.redis.delete(key)
            except Exception as e:
                logger.warning(f"Erro ao deletar do Redis: {e}")
                
        async with self.local_lock:
            self.local_cache.pop(key, None)
            
    async def clear(self) -> None:
        """Limpa todo o cache"""
        if self.redis:
            try:
                await self.redis.flushdb()
            except Exception as e:
                logger.warning(f"Erro ao limpar Redis: {e}")
                
        async with self.local_lock:
            self.local_cache.clear()
            
    async def get_many(
        self,
        keys: list[str],
        use_local: bool = True
    ) -> Dict[str, Any]:
        """
        Obtém múltiplos valores do cache.
        
        Args:
            keys: Lista de chaves
            use_local: Se deve usar cache local
            
        Returns:
            Dicionário com valores encontrados
        """
        result = {}
        
        # Tenta Redis primeiro
        if self.redis:
            try:
                values = await self.redis.mget(keys)
                for key, value in zip(keys, values):
                    if value:
                        result[key] = json.loads(value)
                        CACHE_HITS.labels('redis').inc()
            except Exception as e:
                logger.warning(f"Erro ao ler múltiplos do Redis: {e}")
                
        # Complementa com cache local
        if use_local:
            async with self.local_lock:
                for key in keys:
                    if key not in result and key in self.local_cache:
                        entry = self.local_cache[key]
                        if not self._is_expired(entry):
                            result[key] = entry['value']
                            CACHE_HITS.labels('local').inc()
                        else:
                            del self.local_cache[key]
                            
        # Contabiliza misses
        misses = len(keys) - len(result)
        if misses > 0:
            CACHE_MISSES.labels('all').inc(misses)
            
        return result
        
    async def set_many(
        self,
        mapping: Dict[str, Any],
        ttl: Optional[int] = None,
        use_local: bool = True
    ) -> None:
        """
        Armazena múltiplos valores no cache.
        
        Args:
            mapping: Dicionário com valores
            ttl: Tempo de vida em segundos
            use_local: Se deve usar cache local
        """
        if ttl is None:
            ttl = settings.cache.ttl
            
        # Tenta Redis primeiro
        if self.redis:
            try:
                pipeline = self.redis.pipeline()
                for key, value in mapping.items():
                    pipeline.set(key, json.dumps(value), ex=ttl)
                await pipeline.execute()
            except Exception as e:
                logger.warning(f"Erro ao escrever múltiplos no Redis: {e}")
                
        # Fallback para cache local
        if use_local:
            async with self.local_lock:
                expires_at = datetime.now() + timedelta(seconds=ttl)
                
                # Limpa cache se necessário
                while len(self.local_cache) + len(mapping) > settings.cache.max_size:
                    self._cleanup_local_cache()
                    
                for key, value in mapping.items():
                    self.local_cache[key] = {
                        'value': value,
                        'expires_at': expires_at
                    }
                    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Verifica se entrada do cache expirou"""
        return datetime.now() > entry['expires_at']
        
    def _cleanup_local_cache(self) -> None:
        """Remove entradas expiradas e mais antigas do cache local"""
        # Remove expirados
        expired = [
            k for k, v in self.local_cache.items()
            if self._is_expired(v)
        ]
        for key in expired:
            del self.local_cache[key]
            
        # Se ainda precisar, remove mais antigos
        if len(self.local_cache) >= settings.cache.max_size:
            sorted_items = sorted(
                self.local_cache.items(),
                key=lambda x: x[1]['expires_at']
            )
            to_remove = len(self.local_cache) - settings.cache.max_size + 1
            for key, _ in sorted_items[:to_remove]:
                del self.local_cache[key]
                
    async def health_check(self) -> bool:
        """Verifica saúde do cache"""
        if not self.redis:
            return False
            
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False
            
    async def get_stats(self) -> Dict[str, Union[int, float]]:
        """Retorna estatísticas do cache"""
        stats = {
            'local_size': len(self.local_cache),
            'local_bytes': sum(
                len(json.dumps(entry['value']))
                for entry in self.local_cache.values()
            )
        }
        
        if self.redis:
            try:
                info = await self.redis.info()
                stats.update({
                    'redis_connected': True,
                    'redis_used_memory': info['used_memory'],
                    'redis_hits': info['keyspace_hits'],
                    'redis_misses': info['keyspace_misses'],
                    'redis_evicted': info['evicted_keys']
                })
            except Exception as e:
                logger.warning(f"Erro ao obter estatísticas do Redis: {e}")
                stats['redis_connected'] = False
                
        return stats

# Instância global
cache = Cache()