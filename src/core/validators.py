from typing import Any, Dict
from pydantic import BaseModel, validator

class ConfigValidator(BaseModel):
    @validator("*", pre=True)
    def empty_str_to_none(cls, v: Any) -> Any:
        if v == "":
            return None
        return v

    @validator("REDIS_PASSWORD")
    def validate_redis_password(cls, v: str, values: Dict[str, Any]) -> str:
        env = values.get('ENVIRONMENT', 'development')
        if env == 'production':
            if not v:
                raise ValueError("Redis password is required in production")
            if len(v) < 8:
                raise ValueError("Redis password must be at least 8 characters in production")
        return v or "development_password" 