#!/bin/bash

# Script de backup automático para volumes Docker
# Faz backup de volumes e logs do sistema

# Configurações
BACKUP_DIR="/backup/media-api"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Criar diretório de backup se não existir
mkdir -p "$BACKUP_DIR"

# Função para log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Função para backup de volume
backup_volume() {
    VOLUME_NAME=$1
    log "Iniciando backup do volume $VOLUME_NAME"
    
    # Criar container temporário e copiar dados
    docker run --rm \
        -v $VOLUME_NAME:/source:ro \
        -v $BACKUP_DIR:/backup \
        alpine tar czf "/backup/${VOLUME_NAME}_${DATE}.tar.gz" -C /source .
        
    if [ $? -eq 0 ]; then
        log "Backup do volume $VOLUME_NAME concluído com sucesso"
    else
        log "ERRO: Falha no backup do volume $VOLUME_NAME"
        exit 1
    fi
}

# Backup dos volumes
log "Iniciando processo de backup"

# Volumes do Docker
backup_volume "media-api_redis_data"
backup_volume "media-api_prometheus_data"
backup_volume "media-api_grafana_data"

# Backup dos logs
log "Fazendo backup dos logs"
tar czf "$BACKUP_DIR/logs_${DATE}.tar.gz" ./logs/

# Backup das configurações
log "Fazendo backup das configurações"
tar czf "$BACKUP_DIR/config_${DATE}.tar.gz" ./config/

# Remover backups antigos
log "Removendo backups mais antigos que $RETENTION_DAYS dias"
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Verificar espaço em disco
DISK_USAGE=$(df -h "$BACKUP_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    log "ALERTA: Uso de disco em $DISK_USAGE%. Considere limpar backups antigos."
fi

log "Processo de backup finalizado" 