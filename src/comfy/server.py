"""
Gerenciador do servidor ComfyUI.
"""

import os
import sys
import signal
import asyncio
import subprocess
from pathlib import Path
from typing import Optional
from loguru import logger
import aiohttp

from .config import comfy_settings

class ComfyUIServer:
    """Gerenciador do servidor ComfyUI"""
    
    def __init__(self):
        """Inicializa o gerenciador do servidor"""
        self.process: Optional[subprocess.Popen] = None
        self.comfy_path = Path("ComfyUI")
        self.startup_timeout = 60  # 60 segundos
        self.max_render_time = 300  # 5 minutos
        
    def is_installed(self) -> bool:
        """Verifica se o ComfyUI está instalado"""
        return self.comfy_path.exists() and (self.comfy_path / "main.py").exists()
        
    async def install(self):
        """Instala o ComfyUI"""
        if self.is_installed():
            logger.info("ComfyUI já está instalado")
            return
            
        logger.info("Instalando ComfyUI...")
        
        # Clonar repositório
        subprocess.run(
            ["git", "clone", "https://github.com/comfyanonymous/ComfyUI.git"],
            check=True
        )
        
        # Instalar dependências
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "ComfyUI/requirements.txt"],
            check=True
        )
        
        logger.info("ComfyUI instalado com sucesso")
        
    def create_start_command(self) -> str:
        """Cria comando para iniciar o servidor"""
        cmd_parts = [
            sys.executable,
            "main.py",
            f"--host {comfy_settings.host}",
            f"--port {comfy_settings.port}",
            f"--preview-method {comfy_settings.preview_method}"
        ]
        
        if comfy_settings.listen:
            cmd_parts.append("--listen")
        
        if comfy_settings.enable_cors:
            cmd_parts.append("--enable-cors")
            cmd_parts.append(f"--cors-origins {','.join(comfy_settings.cors_origins)}")
            
        if comfy_settings.enable_api:
            cmd_parts.append("--enable-api")
            
        if comfy_settings.gpu_only:
            cmd_parts.append("--gpu-only")
            
        # Adicionar caminhos dos modelos
        for model_type, path in comfy_settings.extra_model_paths.items():
            cmd_parts.append(f"--extra-model-paths {path}")
            
        # Configurar diretório de outputs
        cmd_parts.append(f"--output-directory {comfy_settings.outputs_dir}")
            
        return " ".join(cmd_parts)
        
    async def start(self):
        """Inicia o servidor ComfyUI"""
        if not self.is_installed():
            await self.install()
            
        if self.process is not None:
            logger.warning("Servidor ComfyUI já está em execução")
            return
            
        # Criar diretórios necessários
        for path in comfy_settings.extra_model_paths.values():
            path.mkdir(parents=True, exist_ok=True)
            
        comfy_settings.outputs_dir.mkdir(parents=True, exist_ok=True)
        comfy_settings.workflows_dir.mkdir(parents=True, exist_ok=True)
        
        # Iniciar servidor
        logger.info("Iniciando servidor ComfyUI...")
        
        os.chdir(self.comfy_path)
        cmd = self.create_start_command()
        
        self.process = subprocess.Popen(
            cmd.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Aguardar servidor iniciar
        await asyncio.sleep(5)
        
        if self.process.poll() is not None:
            raise RuntimeError("Falha ao iniciar servidor ComfyUI")
            
        logger.info("Servidor ComfyUI iniciado com sucesso")
        
    async def stop(self):
        """Para o servidor ComfyUI"""
        if self.process is None:
            logger.warning("Servidor ComfyUI não está em execução")
            return
            
        logger.info("Parando servidor ComfyUI...")
        
        # Enviar sinal SIGTERM
        self.process.send_signal(signal.SIGTERM)
        
        try:
            # Aguardar processo terminar
            await asyncio.sleep(5)
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Se não terminar, força encerramento
            self.process.kill()
            
        self.process = None
        logger.info("Servidor ComfyUI parado com sucesso")
        
    async def restart(self):
        """Reinicia o servidor ComfyUI"""
        await self.stop()
        await self.start()

    async def wait_until_ready(self, timeout: int):
        """
        Aguarda até que o servidor esteja pronto para processar tarefas.
        
        Args:
            timeout: Tempo máximo de espera em segundos
            
        Raises:
            TimeoutError: Se o servidor não ficar pronto no tempo especificado
            RuntimeError: Se ocorrer erro na verificação
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError("Timeout aguardando servidor ficar pronto")
                
            try:
                # Verifica se processo está rodando
                if self.process is None or self.process.poll() is not None:
                    raise RuntimeError("Servidor não está em execução")
                    
                # Tenta fazer uma requisição de status
                async with aiohttp.ClientSession() as session:
                    url = f"http://{comfy_settings.host}:{comfy_settings.port}/system/status"
                    async with session.get(url) as response:
                        if response.status == 200:
                            return True
                            
            except Exception as e:
                logger.debug(f"Servidor ainda não está pronto: {e}")
                
            await asyncio.sleep(1)

    async def execute_task(self, task):
        """
        Executa uma tarefa no ComfyUI.
        
        Args:
            task: Objeto com informações da tarefa
                - input_path: Caminho do arquivo de workflow
                - gpu_id: ID da GPU a ser utilizada
                - output_path: Caminho para salvar resultado
                
        Returns:
            Dict com resultado da execução
            
        Raises:
            RuntimeError: Se ocorrer erro na execução
        """
        if not task.gpu_id:
            raise ValueError("GPU ID é obrigatório")
            
        # Constrói comando com parâmetros necessários
        cmd_parts = [
            sys.executable,
            "main.py",
            f"--input {task.input_path}",
            f"--output {task.output_path}",
            f"--gpu-id {task.gpu_id}",
            "--no-preview"
        ]
        
        if hasattr(task, 'extra_args'):
            cmd_parts.extend(task.extra_args)
            
        cmd = " ".join(cmd_parts)
        
        # Executa comando
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Erro executando tarefa: {stderr.decode()}")
            
        return {
            'status': 'success',
            'output_path': task.output_path,
            'stdout': stdout.decode(),
            'stderr': stderr.decode()
        }

# Instância global do servidor
comfy_server = ComfyUIServer() 