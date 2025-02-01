"""
Gerenciador de cache unificado com suporte a Redis e memória local.
"""

import asyncio
import logging
from typing import Any, Dict, Optional
import aioredis
from prometheus_client import Counter, Gauge

from src.core.config import settings
from src.core.errors import APIError

logger = logging.getLogger(__name__)

# Métricas Prometheus
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

class CacheManager:
    """
    Gerenciador de cache unificado.
    Suporta Redis e cache local com fallback automático.
    """
    def __init__(self):
        self.local_cache: Dict[str, Dict[str, Any]] = {}
        self.local_lock = asyncio.Lock()
        self.redis: Optional[aioredis.Redis] = None
        
    async def _connect_redis(self):
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
            await self._connect_redis()

    def get_connection(self) -> Optional[aioredis.Redis]:
        """Retorna conexão Redis atual"""
        return self.redis

    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Obtém valor do cache.
        Tenta Redis primeiro, fallback para cache local.
        """
        full_key = f"{namespace}:{key}"
        
        try:
            # Tentar Redis primeiro
            if self.redis:
                value = await self.redis.get(full_key)
                if value:
                    CACHE_HITS.labels(type="redis").inc()
                    return value
                    
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
        key: str,
        value: Any,
        namespace: str = "default",
        ttl: Optional[int] = None
    ):
        """
        Define valor no cache.
        Tenta Redis primeiro, fallback para cache local.
        """
        full_key = f"{namespace}:{key}"
        
        try:
            # Tentar Redis primeiro
            if self.redis:
                if ttl:
                    await self.redis.setex(full_key, ttl, value)
                else:
                    await self.redis.set(full_key, value)
                    
            # Backup em cache local
            async with self.local_lock:
                if namespace not in self.local_cache:
                    self.local_cache[namespace] = {}
                self.local_cache[namespace][key] = value
                
        except Exception as e:
            logger.error(f"Erro ao definir no cache: {e}")
            raise CacheError(f"Erro ao definir no cache: {e}")

    async def delete(self, key: str, namespace: str = "default"):
        """Remove valor do cache"""
        full_key = f"{namespace}:{key}"
        
        try:
            # Remover do Redis
            if self.redis:
                await self.redis.delete(full_key)
                
            # Remover do cache local
            async with self.local_lock:
                if namespace in self.local_cache:
                    self.local_cache[namespace].pop(key, None)
                    
        except Exception as e:
            logger.error(f"Erro ao deletar do cache: {e}")
            raise CacheError(f"Erro ao deletar do cache: {e}")

    async def clear(self, namespace: str = "default"):
        """Limpa todo o cache de um namespace"""
        try:
            # Limpar Redis
            if self.redis:
                keys = await self.redis.keys(f"{namespace}:*")
                if keys:
                    await self.redis.delete(*keys)
                    
            # Limpar cache local
            async with self.local_lock:
                self.local_cache[namespace] = {}
                
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
            raise CacheError(f"Erro ao limpar cache: {e}")

# Instância global do gerenciador de cache
cache_manager = CacheManager() 