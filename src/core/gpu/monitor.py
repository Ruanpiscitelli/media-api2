"""
Monitor unificado de GPU que centraliza todas as métricas e monitoramento.
"""

import logging
from datetime import datetime
import asyncio
from typing import Dict, Any, List
from prometheus_client import Gauge, Counter, Histogram, start_http_server
import nvidia_smi
import pynvml

logger = logging.getLogger(__name__)

class GPUMonitor:
    """Monitor unificado de GPU que gerencia todas as métricas e monitoramento"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa o monitor de GPU.
        
        Args:
            config: Configuração do monitor (thresholds, intervalos, etc)
        """
        self.config = config
        self._last_metrics = {}
        self.metrics = self._setup_metrics()
        nvidia_smi.nvmlInit()
        pynvml.nvmlInit()
        
    def _setup_metrics(self) -> Dict[str, Any]:
        """Configura todas as métricas Prometheus"""
        return {
            # Métricas básicas
            'vram_usage': Gauge('gpu_vram_usage_mb', 'VRAM usage in MB', ['device']),
            'vram_total': Gauge('gpu_vram_total_mb', 'Total VRAM in MB', ['device']),
            'utilization': Gauge('gpu_utilization_percent', 'GPU utilization percentage', ['device']),
            'temperature': Gauge('gpu_temperature_celsius', 'GPU temperature in Celsius', ['device']),
            'power_usage': Gauge('gpu_power_usage_watts', 'GPU power usage in watts', ['device']),
            
            # Métricas de clock
            'sm_clock': Gauge('gpu_sm_clock_mhz', 'GPU SM clock in MHz', ['device']),
            'memory_clock': Gauge('gpu_memory_clock_mhz', 'GPU memory clock in MHz', ['device']),
            
            # Métricas de throughput
            'pcie_tx': Gauge('gpu_pcie_tx_bytes', 'GPU PCIe TX throughput', ['device']),
            'pcie_rx': Gauge('gpu_pcie_rx_bytes', 'GPU PCIe RX throughput', ['device']),
            
            # Métricas de codificador/decodificador
            'encoder_util': Gauge('gpu_encoder_utilization_percent', 'GPU encoder utilization', ['device']),
            'decoder_util': Gauge('gpu_decoder_utilization_percent', 'GPU decoder utilization', ['device']),
            
            # Contadores de eventos
            'errors': Counter('gpu_errors_total', 'Total GPU errors', ['device', 'type']),
            'throttling': Counter('gpu_throttling_events_total', 'GPU throttling events', ['device', 'reason']),
            
            # Histogramas
            'allocation_time': Histogram(
                'gpu_memory_allocation_seconds',
                'Time to allocate GPU memory',
                ['device'],
                buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0)
            ),
            'gpu_util': Gauge('gpu_util', 'Utilização da GPU (%)', ['gpu_id']),
            'gpu_mem_used': Gauge('gpu_mem_used', 'VRAM utilizada (bytes)', ['gpu_id']),
            'gpu_nvlink_tx': Gauge('gpu_nvlink_tx', 'Taxa NVLink TX (MB/s)', ['gpu_id', 'peer']),
            'gpu_nvlink_rx': Gauge('gpu_nvlink_rx', 'Taxa NVLink RX (MB/s)', ['gpu_id', 'peer'])
        }
    
    async def start_monitoring(self):
        """Inicia o loop de monitoramento"""
        start_http_server(8001)
        while True:
            try:
                await self._collect_metrics()
                await self._check_alerts()
                await asyncio.sleep(self.config['monitoring']['interval_seconds'])
            except Exception as e:
                logger.error(f"Erro no loop de monitoramento: {e}")
                await asyncio.sleep(5)  # Backoff em caso de erro
    
    async def _collect_metrics(self):
        """Coleta métricas de todas as GPUs"""
        try:
            deviceCount = nvidia_smi.nvmlDeviceGetCount()
            for i in range(deviceCount):
                handle = nvidia_smi.nvmlDeviceGetHandleByIndex(i)
                device = str(i)
                
                # Métricas básicas
                memory = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
                self.metrics['vram_usage'].labels(device=device).set(memory.used / 1024**2)
                self.metrics['vram_total'].labels(device=device).set(memory.total / 1024**2)
                
                util = nvidia_smi.nvmlDeviceGetUtilizationRates(handle)
                self.metrics['utilization'].labels(device=device).set(util.gpu)
                
                temp = nvidia_smi.nvmlDeviceGetTemperature(handle, nvidia_smi.NVML_TEMPERATURE_GPU)
                self.metrics['temperature'].labels(device=device).set(temp)
                
                power = nvidia_smi.nvmlDeviceGetPowerUsage(handle) / 1000.0
                self.metrics['power_usage'].labels(device=device).set(power)
                
                # Clocks
                sm_clock = nvidia_smi.nvmlDeviceGetClockInfo(handle, nvidia_smi.NVML_CLOCK_SM)
                mem_clock = nvidia_smi.nvmlDeviceGetClockInfo(handle, nvidia_smi.NVML_CLOCK_MEM)
                self.metrics['sm_clock'].labels(device=device).set(sm_clock)
                self.metrics['memory_clock'].labels(device=device).set(mem_clock)
                
                # PCIe
                pcie_tx = nvidia_smi.nvmlDeviceGetPcieThroughput(handle, nvidia_smi.NVML_PCIE_UTIL_TX_BYTES)
                pcie_rx = nvidia_smi.nvmlDeviceGetPcieThroughput(handle, nvidia_smi.NVML_PCIE_UTIL_RX_BYTES)
                self.metrics['pcie_tx'].labels(device=device).set(pcie_tx)
                self.metrics['pcie_rx'].labels(device=device).set(pcie_rx)
                
                # Encoder/Decoder
                encoder = nvidia_smi.nvmlDeviceGetEncoderUtilization(handle)
                decoder = nvidia_smi.nvmlDeviceGetDecoderUtilization(handle)
                self.metrics['encoder_util'].labels(device=device).set(encoder[0])
                self.metrics['decoder_util'].labels(device=device).set(decoder[0])
                
                # Atualiza estado interno
                self._last_metrics[device] = {
                    'timestamp': datetime.now(),
                    'memory': {
                        'total': memory.total,
                        'used': memory.used,
                        'free': memory.free
                    },
                    'temperature': temp,
                    'utilization': util.gpu,
                    'power': power,
                    'clocks': {
                        'sm': sm_clock,
                        'memory': mem_clock
                    }
                }
                
                # Utilização básica
                self.metrics['gpu_util'].labels(gpu_id=device).set(util.gpu)
                
                # Memória
                self.metrics['gpu_mem_used'].labels(gpu_id=device).set(memory.used)
                
                # NVLink
                for peer in self.check_nvlink_peers(int(device)):
                    tx = pynvml.nvmlDeviceGetNvLinkUtilizationCounter(handle, peer, 0)
                    rx = pynvml.nvmlDeviceGetNvLinkUtilizationCounter(handle, peer, 1)
                    self.metrics['gpu_nvlink_tx'].labels(gpu_id=device, peer=peer).set(tx)
                    self.metrics['gpu_nvlink_rx'].labels(gpu_id=device, peer=peer).set(rx)
                
        except Exception as e:
            logger.error(f"Erro coletando métricas: {e}")
            self.metrics['errors'].labels(device='all', type='collection').inc()
    
    async def _check_alerts(self):
        """Verifica condições de alerta para todas as GPUs"""
        for device, metrics in self._last_metrics.items():
            try:
                # Temperatura
                if metrics['temperature'] > self.config['monitoring']['temperature_limit']:
                    await self._create_alert(
                        device=device,
                        level='warning',
                        type='temperature',
                        message=f"GPU {device} temperatura alta: {metrics['temperature']}°C"
                    )
                
                # Utilização
                if metrics['utilization'] > self.config['monitoring']['utilization_threshold']:
                    await self._create_alert(
                        device=device,
                        level='warning',
                        type='utilization',
                        message=f"GPU {device} utilização alta: {metrics['utilization']}%"
                    )
                
                # Memória
                memory_used_percent = (metrics['memory']['used'] / metrics['memory']['total']) * 100
                if memory_used_percent > self.config['monitoring']['memory_threshold']:
                    await self._create_alert(
                        device=device,
                        level='warning',
                        type='memory',
                        message=f"GPU {device} memória alta: {memory_used_percent:.1f}%"
                    )
                    
            except Exception as e:
                logger.error(f"Erro verificando alertas para GPU {device}: {e}")
                self.metrics['errors'].labels(device=device, type='alert_check').inc()
    
    async def _create_alert(self, device: str, level: str, type: str, message: str):
        """
        Cria um alerta para uma condição detectada.
        
        Args:
            device: ID do dispositivo
            level: Nível do alerta (warning, critical)
            type: Tipo do alerta
            message: Mensagem descritiva
        """
        logger.warning(f"Alerta GPU {device}: {message}")
        # Aqui você pode integrar com seu sistema de alertas
        # Por exemplo, enviando para um serviço de notificação
        
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna as métricas mais recentes"""
        return self._last_metrics
    
    def __del__(self):
        """Cleanup ao destruir o objeto"""
        try:
            nvidia_smi.nvmlShutdown()
            pynvml.nvmlShutdown()
        except:
            pass

    def check_nvlink_peers(self, gpu_id: int) -> List[int]:
        """
        Retorna lista de GPUs conectadas via NVLink.
        
        Args:
            gpu_id: ID da GPU para verificar conexões NVLink
            
        Returns:
            Lista de IDs das GPUs conectadas via NVLink
        """
        peers = []
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
            
            # Verifica cada link NVLink possível (tipicamente 0-5)
            for link in range(6):
                try:
                    # Verifica se o link está ativo
                    if pynvml.nvmlDeviceGetNvLinkState(handle, link) == pynvml.NVML_FEATURE_ENABLED:
                        # Obtém informações do peer conectado
                        peer_info = pynvml.nvmlDeviceGetNvLinkRemotePciInfo(handle, link)
                        
                        # Encontra o ID da GPU correspondente ao PCI info
                        for i in range(pynvml.nvmlDeviceGetCount()):
                            peer_handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                            if pynvml.nvmlDeviceGetPciInfo(peer_handle).busId == peer_info.busId:
                                if i not in peers and i != gpu_id:
                                    peers.append(i)
                                break
                except pynvml.NVMLError as e:
                    logger.debug(f"Link {link} não disponível para GPU {gpu_id}: {e}")
                    continue
                
        except pynvml.NVMLError as e:
            logger.error(f"Erro ao verificar peers NVLink para GPU {gpu_id}: {e}")
            return []
        
        return peers