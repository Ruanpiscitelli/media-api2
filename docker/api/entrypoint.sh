#!/bin/bash
set -e

# Espera pelos serviços necessários
echo "Aguardando serviços..."

# Redis
until nc -z ${REDIS_HOST} ${REDIS_PORT}; do
    echo "Aguardando Redis..."
    sleep 1
done

# RabbitMQ
until nc -z ${RABBITMQ_HOST} ${RABBITMQ_PORT}; do
    echo "Aguardando RabbitMQ..."
    sleep 1
done

# Verifica GPUs
nvidia-smi > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "GPUs NVIDIA detectadas"
else
    echo "AVISO: Nenhuma GPU NVIDIA detectada"
fi

# Aplica migrações se necessário
if [ "$APPLY_MIGRATIONS" = "true" ]; then
    echo "Aplicando migrações..."
    alembic upgrade head
fi

# Inicializa Prometheus e exportadores
echo "Iniciando exportadores de métricas..."
prometheus-node-exporter &
nvidia-dcgm-exporter &

# Define variáveis de ambiente para o Supervisor
export PYTHONPATH="/app:${PYTHONPATH}"

# Inicia o Supervisor
echo "Iniciando serviços via Supervisor..."
exec supervisord -n -c /etc/supervisor/supervisord.conf 