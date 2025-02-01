#!/bin/bash

echo "🔍 Iniciando debug da API..."

# Verificar processos
echo "Processos Python rodando:"
ps aux | grep python

# Verificar portas
echo -e "\nPortas em uso:"
netstat -tulpn | grep LISTEN

# Verificar logs
echo -e "\nÚltimas linhas do log da API:"
tail -n 50 /workspace/logs/api.log

# Tentar iniciar API em modo debug
echo -e "\nTentando iniciar API em modo debug..."
cd /workspace/media-api2
. /workspace/venv_clean/bin/activate

# Verificar estrutura do projeto
echo -e "\nEstrutura do projeto:"
tree -L 3 src/

# Verificar imports críticos
echo -e "\nTestando imports críticos..."
python -c "
import sys
try:
    from src.main import app
    from src.web.routes import router, gui_app
    from src.config import settings
    print('✅ Importação do app bem sucedida')
except Exception as e:
    print(f'❌ Erro ao importar: {e}')
    sys.exit(1)
"

# Verificar conexão com Redis
echo -e "\nTestando conexão com Redis..."
redis-cli ping

# Verificar permissões
echo -e "\nPermissões dos diretórios:"
ls -la /workspace/
ls -la $WORKSPACE/media-api2/src/

# Verificar configuração
echo -e "\nConfigurações do ambiente:"
env | grep -E "PORT|PATH|PYTHON|VIRTUAL_ENV" 