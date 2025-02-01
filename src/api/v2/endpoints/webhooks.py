"""
Endpoints para gerenciamento de webhooks.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict
from src.core.auth import get_current_user
from src.services.webhook import WebhookService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
webhook_service = WebhookService()

class WebhookRegistration(BaseModel):
    """Modelo para registro de webhook"""
    url: HttpUrl
    events: List[str]
    secret: Optional[str] = None
    description: Optional[str] = None

class WebhookInfo(BaseModel):
    """Modelo para informações do webhook"""
    id: str
    url: str
    events: List[str]
    description: Optional[str]
    created_at: str
    last_triggered: Optional[str]
    status: str

@router.post("/register")
async def register_webhook(
    webhook: WebhookRegistration,
    current_user = Depends(get_current_user)
):
    """Registra um novo webhook"""
    try:
        registered = await webhook_service.register(
            url=str(webhook.url),
            events=webhook.events,
            secret=webhook.secret,
            description=webhook.description,
            user_id=current_user.id
        )
        return {
            "status": "success",
            "webhook_id": registered["webhook_id"]
        }
        
    except Exception as e:
        logger.error(f"Erro no registro do webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list", response_model=List[WebhookInfo])
async def list_webhooks(
    current_user = Depends(get_current_user)
):
    """Lista webhooks registrados"""
    try:
        webhooks = await webhook_service.list_webhooks(
            user_id=current_user.id
        )
        return webhooks
        
    except Exception as e:
        logger.error(f"Erro ao listar webhooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user = Depends(get_current_user)
):
    """Remove um webhook"""
    try:
        await webhook_service.delete_webhook(
            webhook_id=webhook_id,
            user_id=current_user.id
        )
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Erro ao remover webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events")
async def list_events(
    current_user = Depends(get_current_user)
):
    """Lista eventos disponíveis para webhooks"""
    try:
        events = await webhook_service.list_events()
        return {"events": events}
        
    except Exception as e:
        logger.error(f"Erro ao listar eventos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{webhook_id}/history")
async def webhook_history(
    webhook_id: str,
    limit: int = 100,
    current_user = Depends(get_current_user)
):
    """Obtém histórico de execuções do webhook"""
    try:
        history = await webhook_service.get_history(
            webhook_id=webhook_id,
            user_id=current_user.id,
            limit=limit
        )
        return {"history": history}
        
    except Exception as e:
        logger.error(f"Erro ao obter histórico: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    webhook: WebhookRegistration,
    current_user = Depends(get_current_user)
):
    """Atualiza configuração do webhook"""
    try:
        updated = await webhook_service.update_webhook(
            webhook_id=webhook_id,
            url=str(webhook.url),
            events=webhook.events,
            secret=webhook.secret,
            description=webhook.description,
            user_id=current_user.id
        )
        return {
            "status": "success",
            "webhook": updated
        }
        
    except Exception as e:
        logger.error(f"Erro ao atualizar webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    current_user = Depends(get_current_user)
):
    """Envia evento de teste para o webhook"""
    try:
        result = await webhook_service.test_webhook(
            webhook_id=webhook_id,
            user_id=current_user.id
        )
        return {
            "status": "success",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Erro ao testar webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{webhook_id}/enable")
async def enable_webhook(
    webhook_id: str,
    current_user = Depends(get_current_user)
):
    """Ativa um webhook"""
    try:
        await webhook_service.enable_webhook(
            webhook_id=webhook_id,
            user_id=current_user.id
        )
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Erro ao ativar webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{webhook_id}/disable")
async def disable_webhook(
    webhook_id: str,
    current_user = Depends(get_current_user)
):
    """Desativa um webhook"""
    try:
        await webhook_service.disable_webhook(
            webhook_id=webhook_id,
            user_id=current_user.id
        )
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Erro ao desativar webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 