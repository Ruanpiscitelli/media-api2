"""
Endpoints para gerenciamento de configurações do sistema.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.core.config import settings
from src.services.auth import get_current_admin_user
from src.services.settings_manager import SettingsManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings"])

# Schemas
class SystemSettings(BaseModel):
    """Configurações do sistema."""
    gpu_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configurações de GPU (memória, limites etc)"
    )
    rate_limits: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configurações de rate limiting"
    )
    cache_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configurações de cache"
    )
    model_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configurações dos modelos"
    )
    notification_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configurações de notificações"
    )

class SettingUpdate(BaseModel):
    """Atualização de configuração."""
    value: Any = Field(..., description="Novo valor da configuração")
    description: Optional[str] = Field(None, description="Descrição da alteração")

# Endpoints
@router.get("", response_model=SystemSettings)
async def get_settings(
    current_user = Depends(get_current_admin_user)
):
    """
    Obtém todas as configurações do sistema (apenas admin).
    """
    try:
        settings_manager = SettingsManager()
        system_settings = await settings_manager.get_all_settings()
        return system_settings
        
    except Exception as e:
        logger.error(f"Erro obtendo configurações: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{category}", response_model=Dict[str, Any])
async def get_category_settings(
    category: str,
    current_user = Depends(get_current_admin_user)
):
    """
    Obtém configurações de uma categoria específica (apenas admin).
    """
    try:
        settings_manager = SettingsManager()
        category_settings = await settings_manager.get_category_settings(category)
        
        if not category_settings:
            raise HTTPException(
                status_code=404,
                detail=f"Categoria {category} não encontrada"
            )
            
        return category_settings
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro obtendo configurações da categoria {category}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{category}/{setting_key}")
async def update_setting(
    category: str,
    setting_key: str,
    setting_data: SettingUpdate,
    current_user = Depends(get_current_admin_user)
):
    """
    Atualiza uma configuração específica (apenas admin).
    """
    try:
        settings_manager = SettingsManager()
        
        # Verificar se categoria existe
        if not await settings_manager.category_exists(category):
            raise HTTPException(
                status_code=404,
                detail=f"Categoria {category} não encontrada"
            )
            
        # Verificar se configuração existe
        if not await settings_manager.setting_exists(category, setting_key):
            raise HTTPException(
                status_code=404,
                detail=f"Configuração {setting_key} não encontrada"
            )
            
        # Atualizar configuração
        await settings_manager.update_setting(
            category=category,
            key=setting_key,
            value=setting_data.value,
            description=setting_data.description
        )
        
        return {
            "status": "success",
            "message": "Configuração atualizada com sucesso"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro atualizando configuração {category}.{setting_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{category}/reset")
async def reset_category_settings(
    category: str,
    current_user = Depends(get_current_admin_user)
):
    """
    Reseta configurações de uma categoria para valores padrão (apenas admin).
    """
    try:
        settings_manager = SettingsManager()
        
        # Verificar se categoria existe
        if not await settings_manager.category_exists(category):
            raise HTTPException(
                status_code=404,
                detail=f"Categoria {category} não encontrada"
            )
            
        # Resetar configurações
        await settings_manager.reset_category_settings(category)
        
        return {
            "status": "success",
            "message": f"Configurações da categoria {category} resetadas com sucesso"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro resetando configurações da categoria {category}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
async def reset_all_settings(
    current_user = Depends(get_current_admin_user)
):
    """
    Reseta todas as configurações do sistema para valores padrão (apenas admin).
    """
    try:
        settings_manager = SettingsManager()
        await settings_manager.reset_all_settings()
        
        return {
            "status": "success",
            "message": "Todas as configurações foram resetadas com sucesso"
        }
        
    except Exception as e:
        logger.error(f"Erro resetando todas as configurações: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{category}/{setting_key}")
async def get_setting_history(
    category: str,
    setting_key: str,
    limit: int = 10,
    current_user = Depends(get_current_admin_user)
):
    """
    Obtém histórico de alterações de uma configuração (apenas admin).
    """
    try:
        settings_manager = SettingsManager()
        
        # Verificar se categoria e configuração existem
        if not await settings_manager.setting_exists(category, setting_key):
            raise HTTPException(
                status_code=404,
                detail=f"Configuração {category}.{setting_key} não encontrada"
            )
            
        # Obter histórico
        history = await settings_manager.get_setting_history(
            category=category,
            key=setting_key,
            limit=limit
        )
        
        return {
            "history": history,
            "total": len(history)
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Erro obtendo histórico da configuração {category}.{setting_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 