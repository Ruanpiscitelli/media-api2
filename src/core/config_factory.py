from functools import lru_cache
from typing import Dict, Type
from .config import Settings
import os

class ConfigFactory:
    _configs: Dict[str, Type[Settings]] = {}

    @classmethod
    def register(cls, env: str, config_class: Type[Settings]):
        cls._configs[env] = config_class

    @classmethod
    @lru_cache()
    def get_config(cls, env: str = None) -> Settings:
        if env is None:
            env = os.getenv("ENVIRONMENT", "development")
        
        config_class = cls._configs.get(env, Settings)
        return config_class(_env_file=f".env.{env}")

# Uso:
settings = ConfigFactory.get_config() 