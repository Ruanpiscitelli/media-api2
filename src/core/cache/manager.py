"""
Gerenciador de cache multi-nível.
Implementa estratégia de cache em RAM, GPU VRAM e Redis.
"""

import asyncio
import json
import logging
from typing import Any, Optional, Dict
import torch
import aioredis
from prometheus_client import Counter, Histogram
from src.core.config import settings

logger = logging.getLogger(__name__)

# Métricas Prometheus
CACHE_HITS = Counter("cache_hits_total", "Total de hits no cache", ["level"])
CACHE_MISSES = Counter("cache_misses_total", "Total de misses no cache", ["level"])
CACHE_LATENCY = Histogram(
    "cache_operation_latency_seconds",
    "Latência das operações de cache em segundos",
    ["operation", "level"]
)

class BaseCache:
    """Interface base para níveis de cache."""
    
    def __init__(self, name: str):
        self.name = name
        
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
        
    async def set(self, key: str, value: Any, expire: Optional[int] = None):
        raise NotImplementedError
        
    async def delete(self, key: str):
        raise NotImplementedError

class RAMCache(BaseCache):
    """Cache em memória RAM."""
    
    def __init__(self):
        super().__init__("ram")
        self._cache: Dict[str, Any] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        
    def _get_lock(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]
        
    async def get(self, key: str) -> Optional[Any]:
        async with self._get_lock(key):
            return self._cache.get(key)
            
    async def set(self, key: str, value: Any, expire: Optional[int] = None):
        async with self._get_lock(key):
            self._cache[key] = value
            if expire:
                asyncio.create_task(self._expire(key, expire))
                
    async def delete(self, key: str):
        async with self._get_lock(key):
            self._cache.pop(key, None)
            
    async def _expire(self, key: str, expire: int):
        await asyncio.sleep(expire)
        await self.delete(key)

class VRAMCache(BaseCache):
    """Cache em VRAM das GPUs."""
    
    def __init__(self):
        super().__init__("vram")
        self._cache: Dict[str, torch.Tensor] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        
    def _get_lock(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]
        
    async def get(self, key: str) -> Optional[Any]:
        async with self._get_lock(key):
            return self._cache.get(key)
            
    async def set(self, key: str, value: Any, expire: Optional[int] = None):
        async with self._get_lock(key):
            if isinstance(value, torch.Tensor) and not value.is_cuda:
                value = value.cuda()
            self._cache[key] = value
            if expire:
                asyncio.create_task(self._expire(key, expire))
                
    async def delete(self, key: str):
        async with self._get_lock(key):
            if key in self._cache:
                del self._cache[key]
                torch.cuda.empty_cache()
                
    async def _expire(self, key: str, expire: int):
        await asyncio.sleep(expire)
        await self.delete(key)

class RedisCache(BaseCache):
    """Cache distribuído usando Redis."""
    
    def __init__(self):
        super().__init__("redis")
        self.redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            socket_timeout=settings.REDIS_TIMEOUT,
            ssl=settings.REDIS_SSL,
            decode_responses=True
        )
        
    async def get(self, key: str) -> Optional[Any]:
        try:
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Erro ao ler do Redis: {e}")
            return None
            
    async def set(self, key: str, value: Any, expire: Optional[int] = None):
        try:
            data = json.dumps(value)
            await self.redis.set(key, data, ex=expire)
        except Exception as e:
            logger.error(f"Erro ao gravar no Redis: {e}")
            
    async def delete(self, key: str):
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Erro ao deletar do Redis: {e}")

class CacheManager:
    """Gerenciador de cache multi-nível."""
    
    def __init__(self):
        self.levels = {
            "ram": RAMCache(),
            "vram": VRAMCache(),
            "redis": RedisCache()
        }
        self.caches: Dict[str, 'Cache'] = {}
        
    def get_cache(self, namespace: str) -> 'Cache':
        """Retorna uma interface de cache com namespace."""
        if namespace not in self.caches:
            self.caches[namespace] = Cache(self, namespace)
        return self.caches[namespace]

class Cache:
    """Interface de cache com namespace."""
    
    def __init__(self, manager: CacheManager, namespace: str):
        self.manager = manager
        self.namespace = namespace
        
    def _make_key(self, key: str) -> str:
        return f"{self.namespace}:{key}"
        
    async def get(self, key: str) -> Optional[Any]:
        key = self._make_key(key)
        
        # Tenta cada nível em ordem
        for level_name, cache in self.manager.levels.items():
            with CACHE_LATENCY.labels(operation="get", level=level_name).time():
                value = await cache.get(key)
                if value is not None:
                    CACHE_HITS.labels(level=level_name).inc()
                    return value
                CACHE_MISSES.labels(level=level_name).inc()
        return None
        
    async def set(self, key: str, value: Any, expire: Optional[int] = None):
        key = self._make_key(key)
        
        # Armazena em todos os níveis
        for level_name, cache in self.manager.levels.items():
            with CACHE_LATENCY.labels(operation="set", level=level_name).time():
                await cache.set(key, value, expire)
                
    async def delete(self, key: str):
        key = self._make_key(key)
        
        # Remove de todos os níveis
        for level_name, cache in self.manager.levels.items():
            with CACHE_LATENCY.labels(operation="delete", level=level_name).time():
                await cache.delete(key)

# Instância global
cache_manager = CacheManager()