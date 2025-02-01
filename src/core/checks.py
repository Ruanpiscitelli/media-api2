"""
Verificações de sistema e dependências
"""
import sys
import pkg_resources
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

def check_python_version() -> bool:
    """Verifica versão do Python"""
    if sys.version_info < (3, 10):
        logger.error("Python 3.10+ é necessário")
        return False
    return True

def check_dependencies() -> List[Tuple[str, bool]]:
    """Verifica dependências críticas"""
    required = {
        'fastapi': '0.100.0',
        'uvicorn': '0.15.0',
        'sqlalchemy': '2.0.0',
        'redis': '4.0.0',
        'pydantic': '2.0.0'
    }
    
    results = []
    for package, min_version in required.items():
        try:
            version = pkg_resources.get_distribution(package).version
            meets_req = pkg_resources.parse_version(version) >= pkg_resources.parse_version(min_version)
            results.append((package, meets_req))
        except pkg_resources.DistributionNotFound:
            results.append((package, False))
            
    return results

def run_system_checks():
    """Executa todas as verificações"""
    if not check_python_version():
        sys.exit(1)
        
    deps = check_dependencies()
    failed = [pkg for pkg, ok in deps if not ok]
    
    if failed:
        logger.error(f"Dependências faltando ou desatualizadas: {', '.join(failed)}")
        sys.exit(1) 