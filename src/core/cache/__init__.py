"""
Pacote de gerenciamento de cache
"""
from .manager import CacheManager, CacheError, cache_manager, Cache

__all__ = ['CacheManager', 'CacheError', 'cache_manager', 'Cache'] 