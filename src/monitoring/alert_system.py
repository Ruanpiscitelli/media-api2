"""
Sistema de alertas que integra diferentes canais de notificação.
Responsável por gerenciar e distribuir alertas do sistema.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import json
import aiohttp
from pydantic import BaseModel

from src.core.config import settings

# Configuração de logging
logger = logging.getLogger(__name__)

# Modelos Pydantic
class Alert(BaseModel):
    """Modelo para alertas."""
    id: str
    timestamp: datetime
    severity: str
    type: str
    message: str
    source: str
    details: Optional[Dict] = None
    tags: List[str] = []

class AlertRule(BaseModel):
    """Modelo para regras de alerta."""
    id: str
    name: str
    condition: str
    severity: str
    channels: List[str]
    cooldown: int = 300  # 5 minutos
    enabled: bool = True

class AlertSystem:
    """
    Sistema central de alertas.
    """
    
    def __init__(self):
        """
        Inicializa o sistema de alertas.
        """
        # Canais de notificação
        self.notification_channels = {
            'slack': SlackNotifier(),
            'email': EmailNotifier(),
            'pagerduty': PagerDutyNotifier(),
            'webhook': WebhookNotifier()
        }
        
        # Cache de alertas recentes
        self._recent_alerts: Dict[str, datetime] = {}
        
        # Regras de alerta
        self.rules: List[AlertRule] = []
        
        # Estado do sistema
        self._is_running = False
    
    async def start(self):
        """
        Inicia o sistema de alertas.
        """
        if self._is_running:
            return
            
        try:
            # Carrega regras
            await self._load_rules()
            
            # Inicializa canais
            for channel in self.notification_channels.values():
                await channel.initialize()
            
            self._is_running = True
            logger.info("Sistema de alertas iniciado")
            
        except Exception as e:
            logger.error(f"Erro iniciando sistema de alertas: {e}")
            raise
    
    async def stop(self):
        """
        Para o sistema de alertas.
        """
        self._is_running = False
        
        # Fecha conexões dos canais
        for channel in self.notification_channels.values():
            await channel.close()
            
        logger.info("Sistema de alertas parado")
    
    async def process_alert(self, alert: Alert):
        """
        Processa um alerta e envia para canais apropriados.
        
        Args:
            alert: Alerta a ser processado
        """
        try:
            # Verifica cooldown
            if self._is_in_cooldown(alert):
                return
                
            # Aplica regras
            channels = self._get_channels_for_alert(alert)
            
            if not channels:
                return
                
            # Envia para canais
            await self._send_to_channels(alert, channels)
            
            # Atualiza cache
            self._recent_alerts[alert.id] = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Erro processando alerta {alert.id}: {e}")
    
    async def _load_rules(self):
        """
        Carrega regras de alerta da configuração.
        """
        try:
            rules_config = settings.ALERT_RULES
            
            self.rules = [
                AlertRule(**rule)
                for rule in rules_config
            ]
            
            logger.info(f"Carregadas {len(self.rules)} regras de alerta")
            
        except Exception as e:
            logger.error(f"Erro carregando regras de alerta: {e}")
            raise
    
    def _is_in_cooldown(self, alert: Alert) -> bool:
        """
        Verifica se um alerta está em cooldown.
        
        Args:
            alert: Alerta a verificar
            
        Returns:
            True se em cooldown, False caso contrário
        """
        if alert.id not in self._recent_alerts:
            return False
            
        last_time = self._recent_alerts[alert.id]
        cooldown = self._get_cooldown_for_alert(alert)
        
        return (datetime.utcnow() - last_time).total_seconds() < cooldown
    
    def _get_cooldown_for_alert(self, alert: Alert) -> int:
        """
        Retorna tempo de cooldown para um alerta.
        
        Args:
            alert: Alerta
            
        Returns:
            Tempo de cooldown em segundos
        """
        for rule in self.rules:
            if self._alert_matches_rule(alert, rule):
                return rule.cooldown
                
        return 300  # Default 5 minutos
    
    def _get_channels_for_alert(self, alert: Alert) -> List[str]:
        """
        Determina canais para envio do alerta.
        
        Args:
            alert: Alerta
            
        Returns:
            Lista de canais para envio
        """
        channels = set()
        
        for rule in self.rules:
            if rule.enabled and self._alert_matches_rule(alert, rule):
                channels.update(rule.channels)
                
        return list(channels)
    
    def _alert_matches_rule(self, alert: Alert, rule: AlertRule) -> bool:
        """
        Verifica se um alerta corresponde a uma regra.
        
        Args:
            alert: Alerta a verificar
            rule: Regra a aplicar
            
        Returns:
            True se corresponde, False caso contrário
        """
        # TODO: Implementar lógica de matching mais complexa
        return alert.severity == rule.severity
    
    async def _send_to_channels(self, alert: Alert, channels: List[str]):
        """
        Envia alerta para canais especificados.
        
        Args:
            alert: Alerta a enviar
            channels: Lista de canais
        """
        for channel in channels:
            if channel not in self.notification_channels:
                logger.warning(f"Canal de notificação desconhecido: {channel}")
                continue
                
            try:
                await self.notification_channels[channel].send_alert(alert)
                
            except Exception as e:
                logger.error(f"Erro enviando alerta para {channel}: {e}")

class BaseNotifier:
    """Classe base para notificadores."""
    
    async def initialize(self):
        """Inicializa o notificador."""
        pass
    
    async def close(self):
        """Fecha conexões do notificador."""
        pass
    
    async def send_alert(self, alert: Alert):
        """Envia um alerta."""
        raise NotImplementedError()

class SlackNotifier(BaseNotifier):
    """Notificador para Slack."""
    
    def __init__(self):
        self.webhook_url = settings.SLACK_WEBHOOK_URL
        self.session = None
    
    async def initialize(self):
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        if self.session:
            await self.session.close()
    
    async def send_alert(self, alert: Alert):
        if not self.session:
            await self.initialize()
            
        message = self._format_message(alert)
        
        async with self.session.post(
            self.webhook_url,
            json=message
        ) as response:
            if response.status >= 400:
                raise Exception(
                    f"Erro enviando alerta para Slack: {response.status}"
                )
    
    def _format_message(self, alert: Alert) -> Dict:
        color = {
            'critical': '#FF0000',
            'error': '#FF4444',
            'warning': '#FFBB33',
            'info': '#33B5E5'
        }.get(alert.severity, '#33B5E5')
        
        return {
            'attachments': [{
                'color': color,
                'title': f"[{alert.severity.upper()}] {alert.type}",
                'text': alert.message,
                'fields': [
                    {'title': 'Source', 'value': alert.source, 'short': True},
                    {'title': 'Time', 'value': alert.timestamp.isoformat(), 'short': True}
                ] + [
                    {'title': k, 'value': str(v), 'short': True}
                    for k, v in (alert.details or {}).items()
                ],
                'footer': 'Media API Alert System'
            }]
        }

class EmailNotifier(BaseNotifier):
    """Notificador para email."""
    
    def __init__(self):
        # TODO: Implementar notificador de email
        pass
    
    async def send_alert(self, alert: Alert):
        # TODO: Implementar envio de email
        pass

class PagerDutyNotifier(BaseNotifier):
    """Notificador para PagerDuty."""
    
    def __init__(self):
        # TODO: Implementar notificador PagerDuty
        pass
    
    async def send_alert(self, alert: Alert):
        # TODO: Implementar integração PagerDuty
        pass

class WebhookNotifier(BaseNotifier):
    """Notificador para webhooks genéricos."""
    
    def __init__(self):
        self.session = None
        self.webhooks = settings.ALERT_WEBHOOKS
    
    async def initialize(self):
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        if self.session:
            await self.session.close()
    
    async def send_alert(self, alert: Alert):
        if not self.session:
            await self.initialize()
            
        payload = {
            'id': alert.id,
            'timestamp': alert.timestamp.isoformat(),
            'severity': alert.severity,
            'type': alert.type,
            'message': alert.message,
            'source': alert.source,
            'details': alert.details,
            'tags': alert.tags
        }
        
        for webhook in self.webhooks:
            try:
                async with self.session.post(
                    webhook['url'],
                    json=payload,
                    headers=webhook.get('headers', {})
                ) as response:
                    if response.status >= 400:
                        logger.error(
                            f"Erro enviando alerta para webhook {webhook['url']}: "
                            f"status {response.status}"
                        )
                        
            except Exception as e:
                logger.error(
                    f"Erro enviando alerta para webhook {webhook['url']}: {e}"
                ) 