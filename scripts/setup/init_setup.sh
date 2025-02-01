#!/bin/bash
set -e

echo "🚀 Iniciando setup automático do Media API..."

# Variáveis de configuração
DEFAULT_USER="admin"
DEFAULT_PASS="mediaapi2024"
DEFAULT_EMAIL="admin@mediaapi.com"
WORKSPACE="/workspace"
API_DIR="$WORKSPACE/media-api2"
COMFY_DIR="$WORKSPACE/ComfyUI"

# Detectar portas mapeadas
get_mapped_port() {
    local internal_port=$1
    local mapped_port=$(netstat -tlpn | grep ":$internal_port" | awk '{split($4,a,":"); print a[2]}')
    if [ -z "$mapped_port" ]; then
        echo "$internal_port"  # Fallback para porta original
    else
        echo "$mapped_port"
    fi
}

API_PORT=$(get_mapped_port 8000)
GUI_PORT=$(get_mapped_port 8080)
COMFY_PORT=$(get_mapped_port 8188)
REDIS_PORT=$(get_mapped_port 6379)

echo "Portas detectadas:"
echo "API: $API_PORT"
echo "GUI: $GUI_PORT"
echo "ComfyUI: $COMFY_PORT"
echo "Redis: $REDIS_PORT"

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}1. Instalando dependências...${NC}"
apt-get update && apt-get install -y \
    git python3-pip python3-venv redis-server net-tools ffmpeg \
    pkg-config libicu-dev python3-dev jq \
    python3-tk python3-dev python3-setuptools \
    libsm6 libxext6 libxrender-dev libglib2.0-0 \
    imagemagick

# Configurar imagemagick para permitir operações de vídeo
sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml || true
sed -i 's/rights="none" pattern="VIDEO"/rights="read|write" pattern="VIDEO"/' /etc/ImageMagick-6/policy.xml || true

echo -e "${BLUE}2. Configurando diretórios...${NC}"

# Criar grupo para a aplicação
groupadd -f mediaapi

# Adicionar usuário atual ao grupo
usermod -a -G mediaapi $(whoami)

mkdir -p $WORKSPACE/{logs,media,cache,models,config,temp} \
        $WORKSPACE/models/{lora,checkpoints,vae} \
        $WORKSPACE/media/{audio,images,video} \
        $WORKSPACE/temp \
        $WORKSPACE/outputs/suno \
        $WORKSPACE/cache/suno

# Definir propriedade dos diretórios (versão corrigida)
chown -R $(whoami):mediaapi \
    $WORKSPACE/temp \
    $WORKSPACE/outputs \
    $WORKSPACE/cache \
    $WORKSPACE/logs \
    $WORKSPACE/media \
    $WORKSPACE/models \
    $WORKSPACE/config

# Criar estrutura completa do projeto
echo "Criando estrutura de diretórios..."
mkdir -p $API_DIR/src/{api/{v1,v2},core,services,web,utils}
mkdir -p $API_DIR/src/core/cache
mkdir -p $API_DIR/src/generation/suno
mkdir -p $API_DIR/src/generation/video/fast_huayuan
mkdir -p $API_DIR/src/utils

# Criar __init__.py em todos os diretórios Python
find $API_DIR/src -type d -exec touch {}/__init__.py \;

# Criar estrutura básica de autenticação
mkdir -p $API_DIR/src/services
cat > $API_DIR/src/services/auth.py << 'EOF'
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Função que será importada por outros módulos
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Implementação básica
        return {"sub": "user"}  # Placeholder
    except JWTError:
        raise credentials_exception
EOF

# Criar arquivo vazio para endpoints/templates.py
touch $API_DIR/src/api/v2/endpoints/templates.py

# Verificar se os arquivos críticos existem
for file in \
    "src/main.py" \
    "src/services/auth.py" \
    "src/api/v2/endpoints/templates.py"; do
    if [ ! -f "$API_DIR/$file" ]; then
        echo "❌ Arquivo crítico não encontrado: $file"
        exit 1
    fi
done

# Ajustar PYTHONPATH
export PYTHONPATH=$API_DIR:$PYTHONPATH

echo -e "${BLUE}3. Configurando Redis...${NC}"
cat > /etc/redis/redis.conf << EOF
bind 127.0.0.1
port 6379
maxmemory 8gb
maxmemory-policy allkeys-lru
EOF

# Criar arquivo .env se não existir
touch $WORKSPACE/.env

# Gerar senha segura para Redis
REDIS_PASSWORD=$(openssl rand -hex 32)
echo "REDIS_PASSWORD=$REDIS_PASSWORD" >> $WORKSPACE/.env

# Atualizar configuração do Redis
sed -i '/requirepass/d' /etc/redis/redis.conf
echo "requirepass $REDIS_PASSWORD" >> /etc/redis/redis.conf

# Iniciar Redis diretamente
redis-server /etc/redis/redis.conf --daemonize yes

# Verificar se Redis iniciou
sleep 2
if ! redis-cli ping > /dev/null; then
    echo "Erro ao iniciar Redis!"
    exit 1
fi

echo -e "${BLUE}4. Configurando ambiente Python...${NC}"
python3 -m venv $WORKSPACE/venv_clean
. $WORKSPACE/venv_clean/bin/activate

echo -e "${BLUE}5. Instalando dependências Python...${NC}"
pip install --upgrade pip wheel setuptools || { echo "❌ Falha na instalação de pip"; exit 1; }

# Adicionar após o upgrade do pip
pip install ninja==1.11.1.1  # Necessário para compilação CUDA
pip install nvidia-ml-py==12.535.133  # Bindings Python para nvidia-smi

# Adicionar após cada bloco de instalação:
if [ $? -ne 0 ]; then
    echo "❌ Falha na instalação de dependências"
    exit 1
fi

# Instalar dependências críticas primeiro
pip install slowapi fastapi uvicorn redis aioredis itsdangerous starlette semver PyYAML gradio colorama python-slugify typing-extensions pydantic-settings

# Instalar yt-dlp para download de vídeos
pip install yt-dlp==2023.11.16

# Depois as dependências de mídia
pip install --no-cache-dir \
    moviepy==1.0.3 \
    opencv-python-headless==4.8.0.74 \
    ffmpeg-python==0.2.0 \
    Pillow==10.0.0 \
    numpy==1.24.0 \
    scipy==1.11.3 \
    einops==0.6.1 \
    pytorch-lightning==2.0.9 \
    aiofiles==23.2.1 \
    psutil==5.9.5

# Verificar instalação do moviepy
python -c "import moviepy.editor; print('Moviepy instalado com sucesso!')"

# Verificar versão do Python
python --version

# Adicionar antes da instalação do PyTorch
echo -e "${BLUE}Instalando CUDA Toolkit 12.1 e cuDNN...${NC}"

# Configurar variáveis de ambiente do CUDA
export PATH=/usr/local/cuda-12.1/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64:$LD_LIBRARY_PATH

# Verificar execução com Bash
if [ -z "$BASH" ]; then
    echo "❌ Este script requer o Bash. Execute com: bash $0"
    exit 1
fi

# Adicionar antes da instalação do CUDA
echo -e "${BLUE}Configurando repositórios NVIDIA...${NC}"
echo "Configurando repositório CUDA..."
curl -s -L https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin -o /etc/apt/preferences.d/cuda-repository-pin-600
apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub
add-apt-repository -y "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/ /"
apt-get update

# Instalar com prioridade máxima
apt-get install -y --allow-change-held-packages \
    cuda-toolkit-12-1 \
    libcudnn8=8.9.7.29-1+cuda12.2

# Instalar torch primeiro
echo "Instalando PyTorch..."
pip install torch==2.1.0+cu121 torchvision==0.16.0+cu121 torchaudio==2.1.0+cu121 \
    --index-url https://download.pytorch.org/whl/cu121

# Instalar dependências do ComfyUI primeiro
echo "Instalando dependências do ComfyUI..."
cd $COMFY_DIR
pip install -r requirements.txt

# Iniciar ComfyUI em background
echo "Iniciando ComfyUI..."
nohup python main.py \
    --listen 0.0.0.0 \
    --port $COMFY_PORT \
    --disable-auto-launch \
    > /workspace/logs/comfyui.log 2>&1 &

# Depois as outras dependências
echo "Instalando dependências da API..."
cd $API_DIR
pip install -r $API_DIR/requirements/vast.txt
pip install -r $API_DIR/requirements.txt

# Verificar instalação
python -c "import torch; print(f'PyTorch instalado: {torch.__version__}')"
python -c "import fastapi; print(f'FastAPI instalado: {fastapi.__version__}')"

# Verificar todas as dependências críticas
echo "Verificando dependências críticas..."
python << EOF
import sys
try:
    import torch
    import fastapi
    import redis
    import uvicorn
    import PIL
    import moviepy.editor
    import cv2
    import numpy
    import einops
    import pytorch_lightning
    import yt_dlp
    print("✅ Todas as dependências críticas estão instaladas")
except ImportError as e:
    print(f"❌ Erro ao importar dependências: {e}")
    sys.exit(1)
EOF

# Adicionar após a instalação do torch
pip install transformers==4.35.2

# Necessário para distribuição de modelos entre GPUs
pip install accelerate==0.25.0

# Adicionar na seção de dependências CUDA
pip install triton==2.1.0

# Adicionar após instalação do CUDA
pip install nvidia-cudnn-cu12==8.9.7.29 \
    nvidia-cublas-cu12==12.1.3.1 \
    nvidia-cuda-nvrtc-cu12==12.1.105 \
    nvidia-cuda-runtime-cu12==12.1.105

echo -e "${BLUE}Verificando drivers NVIDIA...${NC}"
nvidia-smi --query-gpu=driver_version --format=csv,noheader
if [ $? -ne 0 ]; then
    echo "❌ Drivers NVIDIA não detectados!"
    echo "Instale os drivers compatíveis com CUDA 12.1"
    exit 1
fi

echo -e "${BLUE}6. Iniciando serviços...${NC}"
cd $API_DIR

# Garantir que nenhuma instância antiga esteja rodando
pkill -f "uvicorn" || true
pkill -f "python main.py" || true

# Limpar arquivos temporários
rm -f /workspace/logs/api.log

# Iniciar API com log mais detalhado
echo "Iniciando API com um worker..."
export PYTHONPATH=$API_DIR:$PYTHONPATH
export LOG_LEVEL=debug

nohup uvicorn src.main:app \
    --host 0.0.0.0 \
    --port $API_PORT \
    --workers 1 \
    --log-level debug \
    --reload \
    --reload-dir src \
    > /workspace/logs/api.log 2>&1 &
API_PID=$!

# Log do processo
echo "PID da API: $API_PID"
ps -p $API_PID -o pid,ppid,cmd

# Aguardar API iniciar (com timeout)
echo "Aguardando API iniciar..."
MAX_TRIES=30
COUNT=0
while ! curl -s http://localhost:$API_PORT/health > /dev/null && [ $COUNT -lt $MAX_TRIES ]; do
    echo "Tentativa $((COUNT+1)) de $MAX_TRIES..."
    if ! ps -p $API_PID > /dev/null; then
        echo "Processo da API morreu! Verificando logs:"
        tail -n 50 /workspace/logs/api.log
        exit 1
    fi
    sleep 2
    COUNT=$((COUNT+1))

    # Mostrar logs em tempo real
    tail -n 5 /workspace/logs/api.log
done

if [ $COUNT -eq $MAX_TRIES ]; then
    echo "Erro: API não iniciou após $MAX_TRIES tentativas"
    echo "Últimas linhas do log:"
    tail -n 20 $WORKSPACE/logs/api.log
    exit 1
fi

echo "API iniciada com sucesso!"

echo -e "${BLUE}7. Criando usuário padrão...${NC}"
curl -X POST http://localhost:$API_PORT/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$DEFAULT_USER\",
    \"password\": \"$DEFAULT_PASS\",
    \"email\": \"$DEFAULT_EMAIL\",
    \"role\": \"admin\"
  }" || { echo "❌ Falha ao criar usuário"; exit 1; }

# Obter e salvar token
TOKEN=$(curl -s -X POST http://localhost:$API_PORT/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$DEFAULT_USER\",
    \"password\": \"$DEFAULT_PASS\"
  }" | jq -r '.access_token')

echo $TOKEN > $WORKSPACE/token.txt

echo -e "${GREEN}✅ Setup concluído!${NC}"
echo -e "Usuário: $DEFAULT_USER"
echo -e "Senha: $DEFAULT_PASS"
echo -e "Token salvo em: $WORKSPACE/token.txt"
echo -e "API rodando em: http://localhost:$API_PORT"
echo -e "GUI em: http://localhost:$GUI_PORT"
echo -e "ComfyUI em: http://localhost:$COMFY_PORT"

# Criar script de reinicialização
cat > $WORKSPACE/restart.sh << EOF
#!/bin/bash

echo "Reiniciando serviços..."

# Detectar portas novamente (podem ter mudado)
API_PORT=\$(netstat -tlpn | grep ":8000" | awk '{split(\$4,a,":"); print a[2]}')
API_PORT=\${API_PORT:-8000}  # Fallback para 8000 se não encontrar

. \$WORKSPACE/venv_clean/bin/activate

# Reiniciar Redis
pkill -f redis-server
redis-server /etc/redis/redis.conf --daemonize yes
sleep 2

if ! redis-cli ping > /dev/null; then
    echo "Erro ao reiniciar Redis!"
    exit 1
fi

# Reiniciar API
pkill -f "uvicorn"
cd $API_DIR
nohup uvicorn src.main:app --host 0.0.0.0 --port \$API_PORT --workers \$(nproc) > $WORKSPACE/logs/api.log 2>&1 &

# Reautenticar
sleep 5
TOKEN=\$(curl -s -X POST http://localhost:\$API_PORT/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "$DEFAULT_USER",
    "password": "$DEFAULT_PASS"
  }' | jq -r '.access_token')

echo \$TOKEN > $WORKSPACE/token.txt
echo "Serviços reiniciados! Novo token gerado."
echo "API rodando em: http://localhost:\$API_PORT"
EOF

chmod +x $WORKSPACE/restart.sh

# Criar arquivo de credenciais
cat > $WORKSPACE/credentials.txt << EOF
Usuário: $DEFAULT_USER
Senha: $DEFAULT_PASS
URL API: http://localhost:$API_PORT
URL GUI: http://localhost:$GUI_PORT
URL ComfyUI: http://localhost:$COMFY_PORT

Para reiniciar os serviços use:
./restart.sh

Para usar o token:
export TOKEN=$(cat /workspace/token.txt)
EOF

echo -e "${BLUE}Credenciais salvas em: $WORKSPACE/credentials.txt${NC}"

# Configurar variáveis de ambiente
cat > $WORKSPACE/.env << EOF
DEBUG=True
REDIS_HOST=localhost
REDIS_PORT=6379
JWT_SECRET_KEY=$TOKEN
JWT_ALGORITHM=HS256
RATE_LIMIT_PER_MINUTE=60
COMFY_API_URL=http://localhost:8188/api
COMFY_WS_URL=ws://localhost:8188/ws
MAX_CONCURRENT_RENDERS=4
MAX_RENDER_TIME=300
MAX_VIDEO_LENGTH=300
MAX_VIDEO_SIZE=100000000
RENDER_TIMEOUT_SECONDS=300
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_DB=0
REDIS_TIMEOUT=5
REDIS_SSL=false
EOF

# Carregar variáveis
set -a
source $WORKSPACE/.env
set +a

# Criar arquivo de rate limiting
cat > $API_DIR/src/core/rate_limit.py << 'EOF'
"""
Módulo para controle de rate limiting usando Redis.
"""

from fastapi import Request, HTTPException, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.core.config import settings
import redis
import logging

logger = logging.getLogger(__name__)

# Configurar conexão Redis
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True
)

# Configurar limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
)

async def rate_limiter(request: Request):
    """
    Middleware para controle de rate limiting.
    
    Args:
        request: Request do FastAPI
        
    Raises:
        HTTPException: Se o limite de requisições for excedido
    """
    try:
        # Obter IP do cliente
        client_ip = get_remote_address(request)
        
        # Chave única para o cliente
        key = f"rate_limit:{client_ip}"
        
        # Verificar limite
        requests = redis_client.incr(key)
        
        # Se primeira requisição, definir TTL
        if requests == 1:
            redis_client.expire(key, 60)  # 60 segundos
            
        # Se excedeu limite
        if requests > settings.RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail="Too many requests"
            )
            
    except redis.RedisError as e:
        logger.error(f"Erro no Redis: {e}")
        # Em caso de erro no Redis, permite a requisição
        pass
    
    except Exception as e:
        logger.error(f"Erro no rate limiting: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
EOF

# Criar arquivo de gerenciamento de GPU
touch $API_DIR/src/core/gpu_manager.py

# Criar gerenciador de fila
cat > $API_DIR/src/core/queue_manager.py << 'EOF'
"""
Gerenciador de fila para processamento de tarefas.
"""
from typing import Dict, Any, Optional
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class QueueManager:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.queue = asyncio.Queue()
        self.processing = False
    
    async def add_task(self, task_id: str, task_data: Dict[str, Any]):
        """Adiciona uma tarefa à fila."""
        self.tasks[task_id] = {
            "status": "queued",
            "data": task_data,
            "created_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None
        }
        await self.queue.put(task_id)
        logger.info(f"Tarefa {task_id} adicionada à fila")
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retorna o status de uma tarefa."""
        return self.tasks.get(task_id)
    
    async def process_queue(self):
        """Processa tarefas da fila."""
        if self.processing:
            return
        
        self.processing = True
        try:
            while True:
                task_id = await self.queue.get()
                task = self.tasks[task_id]
                
                try:
                    task["status"] = "processing"
                    task["started_at"] = datetime.utcnow()
                    
                    # Processamento real será implementado pelos serviços
                    logger.info(f"Processando tarefa {task_id}")
                    
                    task["status"] = "completed"
                    task["completed_at"] = datetime.utcnow()
                    
                except Exception as e:
                    logger.error(f"Erro ao processar tarefa {task_id}: {e}")
                    task["status"] = "failed"
                    task["error"] = str(e)
                    task["completed_at"] = datetime.utcnow()
                
                finally:
                    self.queue.task_done()
                    
        except Exception as e:
            logger.error(f"Erro no processamento da fila: {e}")
        finally:
            self.processing = False

# Instância global
queue_manager = QueueManager()
EOF

# Criar módulo de processamento de áudio
cat > $API_DIR/src/utils/audio.py << 'EOF'
"""
Utilitários para processamento de áudio.
"""
import logging
from pathlib import Path
from typing import Optional
import torch
import torchaudio

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"AudioProcessor inicializado no dispositivo: {self.device}")
    
    async def process_audio(
        self,
        input_path: Path,
        output_path: Path,
        sample_rate: int = 44100,
        normalize: bool = True
    ) -> Optional[Path]:
        """
        Processa um arquivo de áudio.
        
        Args:
            input_path: Caminho do arquivo de entrada
            output_path: Caminho do arquivo de saída
            sample_rate: Taxa de amostragem desejada
            normalize: Se deve normalizar o áudio
            
        Returns:
            Path do arquivo processado ou None se falhar
        """
        try:
            # Carregar áudio
            waveform, sr = torchaudio.load(input_path)
            
            # Converter para mono se necessário
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Resample se necessário
            if sr != sample_rate:
                resampler = torchaudio.transforms.Resample(sr, sample_rate)
                waveform = resampler(waveform)
            
            # Normalizar se solicitado
            if normalize:
                waveform = waveform / torch.max(torch.abs(waveform))
            
            # Salvar
            torchaudio.save(output_path, waveform, sample_rate)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Erro ao processar áudio: {e}")
            return None

# Instância global
audio_processor = AudioProcessor()
EOF

# Criar arquivo de autenticação
cat > $API_DIR/src/core/auth.py << 'EOF'
"""
Módulo central de autenticação.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from src.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Valida o token JWT e retorna o usuário atual.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return {"sub": username}
    except JWTError:
        raise credentials_exception
EOF

# Criar módulo FastHuayuan
cat > $API_DIR/src/generation/video/fast_huayuan/__init__.py << 'EOF'
"""
Módulo para geração de vídeos usando FastHuayuan.
"""
from typing import Optional, Dict, Any
import torch
import logging

logger = logging.getLogger(__name__)

class FastHuayuanGenerator:
    """Gerador de vídeos usando FastHuayuan."""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        logger.info(f"FastHuayuan inicializado no dispositivo: {self.device}")
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Gera um vídeo a partir do prompt.
        
        Args:
            prompt: Descrição do vídeo a ser gerado
            **kwargs: Parâmetros adicionais
            
        Returns:
            Dict com informações do vídeo gerado
        """
        try:
            # TODO: Implementar geração real
            return {
                "status": "success",
                "message": "Geração simulada - implementação pendente"
            }
        except Exception as e:
            logger.error(f"Erro na geração: {e}")
            raise
EOF

# Criar módulos Suno
cat > $API_DIR/src/generation/suno/bark_voice.py << 'EOF'
"""
Gerador de voz usando Bark.
"""
from typing import Optional, Dict, Any
import torch
import logging

logger = logging.getLogger(__name__)

class BarkVoiceGenerator:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"BarkVoice inicializado no dispositivo: {self.device}")
    
    async def generate(self, text: str, **kwargs) -> Dict[str, Any]:
        """Placeholder para geração de voz."""
        return {"status": "success", "message": "Implementação pendente"}
EOF

cat > $API_DIR/src/generation/suno/musicgen.py << 'EOF'
"""
Gerador de música usando MusicGen.
"""
from typing import Optional, Dict, Any
import torch
import logging

logger = logging.getLogger(__name__)

class MusicGenerator:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"MusicGen inicializado no dispositivo: {self.device}")
    
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Placeholder para geração de música."""
        return {"status": "success", "message": "Implementação pendente"}
EOF