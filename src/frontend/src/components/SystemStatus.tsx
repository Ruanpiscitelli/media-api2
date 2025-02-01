import React, { useEffect, useState } from 'react';
import {
  HStack,
  Badge,
  Tooltip,
  Text,
} from '@chakra-ui/react';

interface SystemMetrics {
  gpu_utilization: number;
  vram_usage: number;
  queue_size: number;
}

export function SystemStatus() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      const response = await fetch('/api/v1/system/metrics');
      const data = await response.json();
      setMetrics(data);
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!metrics) return null;

  return (
    <HStack spacing={4}>
      <Tooltip label="GPU Utilization">
        <Badge colorScheme={metrics.gpu_utilization > 80 ? 'red' : 'green'}>
          GPU: {metrics.gpu_utilization}%
        </Badge>
      </Tooltip>

      <Tooltip label="VRAM Usage">
        <Badge colorScheme={metrics.vram_usage > 80 ? 'red' : 'green'}>
          VRAM: {metrics.vram_usage}%
        </Badge>
      </Tooltip>

      <Tooltip label="Queue Size">
        <Badge colorScheme={metrics.queue_size > 5 ? 'yellow' : 'green'}>
          Queue: {metrics.queue_size}
        </Badge>
      </Tooltip>
    </HStack>
  );
} 