"""
Script para executar todos os testes com cobertura.
"""

import os
import sys
import unittest
import coverage
from pathlib import Path

def run_tests():
    """Executa todos os testes com cobertura"""
    # Configurar cobertura
    cov = coverage.Coverage(
        branch=True,
        source=[str(Path(__file__).parent.parent / "src")],
        omit=["*/__init__.py", "*/tests/*"]
    )
    cov.start()
    
    # Descobrir e executar testes
    loader = unittest.TestLoader()
    tests_dir = Path(__file__).parent
    suite = loader.discover(str(tests_dir))
    
    # Executar testes
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Gerar relatório de cobertura
    cov.stop()
    cov.save()
    
    print("\nRelatório de Cobertura:")
    cov.report()
    
    # Gerar relatório HTML
    html_dir = tests_dir / "coverage_html"
    html_dir.mkdir(exist_ok=True)
    cov.html_report(directory=str(html_dir))
    
    print(f"\nRelatório HTML gerado em: {html_dir}")
    
    # Retornar código de saída
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests()) 