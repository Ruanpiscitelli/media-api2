"""
Gerenciador de cache multi-nível.
Implementa estratégia de cache em RAM, GPU VRAM e Redis.
"""

import asyncio
from typing import Any, Optional, Dict
import logging
import json
import hashlib

import torch
import redis.asyncio as redis
from prometheus_client import Counter, Histogram

from src.core.config import settings


# Métricas Prometheus
CACHE_HITS = Counter("cache_hits_total", "Total cache hits", ["level"])
CACHE_MISSES = Counter("cache_misses_total", "Total cache misses", ["level"])
CACHE_LATENCY = Histogram(
    "cache_operation_latency_seconds",
    "Cache operation latency in seconds",
    ["operation", "level"]
)


class CacheLevel:
    """Interface base para níveis de cache."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"cache.{name}")
    
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        raise NotImplementedError
    
    async def delete(self, key: str):
        raise NotImplementedError
    
    async def exists(self, key: str) -> bool:
        raise NotImplementedError


class RAMCache(CacheLevel):
    """Cache em memória RAM usando dicionário."""
    
    def __init__(self):
        super().__init__("ram")
        self._cache: Dict[str, Any] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
    
    def _get_lock(self, key: str) -> asyncio.Lock:
        """Retorna ou cria um lock para a chave."""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._get_lock(key):
            return self._cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        async with self._get_lock(key):
            self._cache[key] = value
            
            if ttl:
                asyncio.create_task(self._expire(key, ttl))
    
    async def delete(self, key: str):
        async with self._get_lock(key):
            self._cache.pop(key, None)
    
    async def exists(self, key: str) -> bool:
        return key in self._cache
    
    async def _expire(self, key: str, ttl: int):
        """Remove a chave após o TTL."""
        await asyncio.sleep(ttl)
        await self.delete(key)


class VRAMCache(CacheLevel):
    """Cache em VRAM das GPUs."""
    
    def __init__(self):
        super().__init__("vram")
        self._cache: Dict[str, torch.Tensor] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
    
    def _get_lock(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]
    
    async def get(self, key: str) -> Optional[torch.Tensor]:
        async with self._get_lock(key):
            return self._cache.get(key)
    
    async def set(self, key: str, value: torch.Tensor, ttl: Optional[int] = None):
        async with self._get_lock(key):
            # Move tensor para GPU se não estiver
            if not value.is_cuda:
                value = value.cuda()
            
            self._cache[key] = value
            
            if ttl:
                asyncio.create_task(self._expire(key, ttl))
    
    async def delete(self, key: str):
        async with self._get_lock(key):
            if key in self._cache:
                del self._cache[key]
                torch.cuda.empty_cache()
    
    async def exists(self, key: str) -> bool:
        return key in self._cache
    
    async def _expire(self, key: str, ttl: int):
        await asyncio.sleep(ttl)
        await self.delete(key)


class RedisCache(CacheLevel):
    """Cache distribuído usando Redis."""
    
    def __init__(self):
        super().__init__("redis")
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
    
    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        await self.redis.set(
            key,
            json.dumps(value),
            ex=ttl
        )
    
    async def delete(self, key: str):
        await self.redis.delete(key)
    
    async def exists(self, key: str) -> bool:
        return await self.redis.exists(key) > 0
    
    def pipeline(self):
        """Retorna um pipeline Redis para operações em lote."""
        return self.redis.pipeline()


class CacheManager:
    """Gerenciador de cache multi-nível."""
    
    def __init__(self):
        self.logger = logging.getLogger("cache.manager")
        self.levels = {
            "ram": RAMCache(),
            "vram": VRAMCache(),
            "redis": RedisCache()
        }
    
    def get_cache(self, namespace: str) -> "NamespacedCache":
        """Retorna uma interface de cache com namespace."""
        return NamespacedCache(self, namespace)
    
    async def get(self, key: str, level: Optional[str] = None) -> Optional[Any]:
        """Busca um valor no cache, tentando todos os níveis."""
        if level:
            return await self._get_from_level(key, level)
        
        # Tenta cada nível em ordem
        for level_name in ["ram", "vram", "redis"]:
            with CACHE_LATENCY.labels(operation="get", level=level_name).time():
                value = await self._get_from_level(key, level_name)
                if value is not None:
                    CACHE_HITS.labels(level=level_name).inc()
                    return value
                CACHE_MISSES.labels(level=level_name).inc()
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        level: Optional[str] = None
    ):
        """Armazena um valor no cache."""
        if level:
            await self._set_in_level(key, value, level, ttl)
        else:
            # Armazena em todos os níveis
            for level_name in ["ram", "vram", "redis"]:
                with CACHE_LATENCY.labels(operation="set", level=level_name).time():
                    await self._set_in_level(key, value, level_name, ttl)
    
    async def delete(self, key: str, level: Optional[str] = None):
        """Remove um valor do cache."""
        if level:
            await self._delete_from_level(key, level)
        else:
            # Remove de todos os níveis
            for level_name in ["ram", "vram", "redis"]:
                with CACHE_LATENCY.labels(operation="delete", level=level_name).time():
                    await self._delete_from_level(key, level_name)
    
    async def exists(self, key: str, level: Optional[str] = None) -> bool:
        """Verifica se uma chave existe no cache."""
        if level:
            return await self._exists_in_level(key, level)
        
        # Verifica em todos os níveis
        for level_name in ["ram", "vram", "redis"]:
            if await self._exists_in_level(key, level_name):
                return True
        
        return False
    
    async def _get_from_level(self, key: str, level: str) -> Optional[Any]:
        """Busca um valor em um nível específico."""
        try:
            return await self.levels[level].get(key)
        except Exception as e:
            self.logger.error(f"Erro ao buscar do cache {level}: {e}")
            return None
    
    async def _set_in_level(
        self,
        key: str,
        value: Any,
        level: str,
        ttl: Optional[int] = None
    ):
        """Armazena um valor em um nível específico."""
        try:
            await self.levels[level].set(key, value, ttl)
        except Exception as e:
            self.logger.error(f"Erro ao armazenar no cache {level}: {e}")
    
    async def _delete_from_level(self, key: str, level: str):
        """Remove um valor de um nível específico."""
        try:
            await self.levels[level].delete(key)
        except Exception as e:
            self.logger.error(f"Erro ao remover do cache {level}: {e}")
    
    async def _exists_in_level(self, key: str, level: str) -> bool:
        """Verifica se uma chave existe em um nível específico."""
        try:
            return await self.levels[level].exists(key)
        except Exception as e:
            self.logger.error(f"Erro ao verificar existência no cache {level}: {e}")
            return False


class NamespacedCache:
    """Interface de cache com namespace."""
    
    def __init__(self, manager: CacheManager, namespace: str):
        self.manager = manager
        self.namespace = namespace
    
    def _get_namespaced_key(self, key: str) -> str:
        """Gera uma chave com namespace."""
        return f"{self.namespace}:{key}"
    
    async def get(self, key: str, level: Optional[str] = None) -> Optional[Any]:
        return await self.manager.get(
            self._get_namespaced_key(key),
            level
        )
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        level: Optional[str] = None
    ):
        await self.manager.set(
            self._get_namespaced_key(key),
            value,
            ttl,
            level
        )
    
    async def delete(self, key: str, level: Optional[str] = None):
        await self.manager.delete(
            self._get_namespaced_key(key),
            level
        )
    
    async def exists(self, key: str, level: Optional[str] = None) -> bool:
        return await self.manager.exists(
            self._get_namespaced_key(key),
            level
        )


# Instância global do gerenciador
cache_manager = CacheManager() 