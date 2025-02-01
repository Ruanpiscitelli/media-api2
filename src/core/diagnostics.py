"""
Módulo de diagnóstico para identificar e corrigir problemas na inicialização da API
"""
import os
import sys
import logging
import importlib
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import redis
import psutil
import uvicorn

logger = logging.getLogger(__name__)

class APIDiagnostics:
    def __init__(self):
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.fixes_applied: List[str] = []

    async def run_full_diagnostic(self) -> bool:
        """Executa diagnóstico completo do sistema"""
        try:
            # 1. Verificar ambiente Python
            self._check_python_environment()
            
            # 2. Verificar dependências
            self._check_dependencies()
            
            # 3. Verificar configurações
            await self._check_settings()
            
            # 4. Verificar sistema de arquivos
            self._check_filesystem()
            
            # 5. Verificar serviços externos
            await self._check_external_services()
            
            # 6. Verificar GPUs
            self._check_gpu_setup()
            
            # 7. Aplicar correções
            if self.errors:
                await self._apply_fixes()
            
            return len(self.errors) == 0

        except Exception as e:
            logger.error(f"Erro durante diagnóstico: {str(e)}")
            self.errors.append({
                "type": "diagnostic_error",
                "message": str(e),
                "critical": True
            })
            return False

    def _check_python_environment(self):
        """Verifica ambiente Python"""
        # Verificar versão do Python
        if sys.version_info < (3, 9):
            self.errors.append({
                "type": "python_version",
                "message": f"Python 3.9+ requerido, encontrado {sys.version}",
                "fix": "upgrade_python"
            })

        # Verificar ambiente virtual
        if not hasattr(sys, 'real_prefix') and not sys.base_prefix != sys.prefix:
            self.warnings.append({
                "type": "venv_missing",
                "message": "Ambiente virtual não detectado"
            })

    def _check_dependencies(self):
        """Verifica dependências do projeto"""
        required_packages = [
            'fastapi', 'uvicorn', 'redis', 'pydantic',
            'python-jose[cryptography]', 'passlib[bcrypt]'
        ]
        
        for package in required_packages:
            try:
                importlib.import_module(package.split('[')[0])
            except ImportError:
                self.errors.append({
                    "type": "missing_dependency",
                    "message": f"Pacote {package} não encontrado",
                    "fix": "install_package",
                    "package": package
                })

    async def _check_settings(self):
        """Verifica configurações da aplicação"""
        try:
            from src.core.config import settings
            
            # Verificar secret_key
            if not settings.secret_key:
                self.errors.append({
                    "type": "missing_secret_key",
                    "message": "SECRET_KEY não configurada",
                    "fix": "generate_secret_key"
                })
            
            # Verificar caminhos críticos
            critical_paths = [
                settings.MEDIA_DIR,
                settings.MODELS_DIR,
                settings.paths.temp,
                settings.paths.logs
            ]
            
            for path in critical_paths:
                if not path.exists():
                    self.errors.append({
                        "type": "missing_directory",
                        "message": f"Diretório não encontrado: {path}",
                        "fix": "create_directory",
                        "path": path
                    })

        except Exception as e:
            self.errors.append({
                "type": "settings_error",
                "message": f"Erro nas configurações: {str(e)}",
                "critical": True
            })

    def _check_filesystem(self):
        """Verifica sistema de arquivos"""
        required_permissions = [
            ("/workspace", "rwx"),
            ("/workspace/logs", "rwx"),
            ("/workspace/media", "rwx"),
            ("/tmp", "rwx")
        ]
        
        for path, required_perms in required_permissions:
            if not os.path.exists(path):
                self.errors.append({
                    "type": "missing_path",
                    "message": f"Caminho não encontrado: {path}",
                    "fix": "create_directory",
                    "path": path
                })
                continue
                
            # Verificar permissões
            current_perms = oct(os.stat(path).st_mode)[-3:]
            if not self._check_permissions(current_perms, required_perms):
                self.errors.append({
                    "type": "invalid_permissions",
                    "message": f"Permissões inválidas em {path}",
                    "fix": "fix_permissions",
                    "path": path,
                    "required": required_perms
                })

    async def _check_external_services(self):
        """Verifica serviços externos"""
        # Verificar Redis
        try:
            from src.core.config import settings
            r = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                socket_timeout=1
            )
            r.ping()
        except Exception as e:
            self.errors.append({
                "type": "redis_error",
                "message": f"Erro ao conectar ao Redis: {str(e)}",
                "fix": "start_redis"
            })

    def _check_gpu_setup(self):
        """Verifica configuração das GPUs"""
        try:
            import torch
            if not torch.cuda.is_available():
                self.warnings.append({
                    "type": "gpu_not_available",
                    "message": "CUDA não disponível"
                })
            else:
                # Verificar memória disponível
                for i in range(torch.cuda.device_count()):
                    free_mem = torch.cuda.get_device_properties(i).total_memory
                    if free_mem < 8 * 1024 * 1024 * 1024:  # 8GB
                        self.warnings.append({
                            "type": "low_gpu_memory",
                            "message": f"GPU {i} com pouca memória: {free_mem/1024/1024/1024:.1f}GB"
                        })
        except ImportError:
            self.warnings.append({
                "type": "torch_not_found",
                "message": "PyTorch não instalado"
            })

    async def _apply_fixes(self):
        """Aplica correções para os problemas encontrados"""
        for error in self.errors:
            if error.get("fix") == "install_package":
                subprocess.run([
                    sys.executable, "-m", "pip", "install",
                    error["package"]
                ])
                self.fixes_applied.append(f"Instalado {error['package']}")
                
            elif error.get("fix") == "create_directory":
                os.makedirs(error["path"], exist_ok=True)
                self.fixes_applied.append(f"Criado diretório {error['path']}")
                
            elif error.get("fix") == "fix_permissions":
                os.chmod(error["path"], 0o755)
                self.fixes_applied.append(f"Corrigidas permissões de {error['path']}")
                
            elif error.get("fix") == "start_redis":
                subprocess.run(["service", "redis-server", "start"])
                self.fixes_applied.append("Iniciado servidor Redis")
                
            elif error.get("fix") == "generate_secret_key":
                import secrets
                os.environ["SECRET_KEY"] = secrets.token_urlsafe(32)
                self.fixes_applied.append("Gerada nova SECRET_KEY")

    def _check_permissions(self, current: str, required: str) -> bool:
        """Verifica se as permissões atuais atendem aos requisitos"""
        permission_map = {'r': 4, 'w': 2, 'x': 1}
        current_num = int(current, 8)
        required_num = sum(permission_map[p] for p in required)
        return (current_num & required_num) == required_num

    def print_report(self):
        """Imprime relatório do diagnóstico"""
        print("\n=== Relatório de Diagnóstico ===")
        
        if self.errors:
            print("\nErros encontrados:")
            for error in self.errors:
                print(f"❌ {error['message']}")
        
        if self.warnings:
            print("\nAvisos:")
            for warning in self.warnings:
                print(f"⚠️ {warning['message']}")
        
        if self.fixes_applied:
            print("\nCorreções aplicadas:")
            for fix in self.fixes_applied:
                print(f"✅ {fix}")
        
        if not self.errors and not self.warnings:
            print("✅ Nenhum problema encontrado!")

async def run_diagnostics():
    """Função auxiliar para executar diagnóstico"""
    diagnostics = APIDiagnostics()
    success = await diagnostics.run_full_diagnostic()
    diagnostics.print_report()
    return success 