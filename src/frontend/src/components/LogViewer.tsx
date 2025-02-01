import React, { useEffect, useState, useRef } from 'react';
import {
  Box,
  VStack,
  Text,
  Select,
  Button,
  Code,
  useColorModeValue,
  HStack
} from '@chakra-ui/react';
import { DownloadIcon, RepeatIcon } from '@chakra-ui/icons';

interface Log {
  timestamp: string;
  level: string;
  message: string;
}

export function LogViewer() {
  const [logs, setLogs] = useState<Log[]>([]);
  const [selectedService, setSelectedService] = useState('all');
  const logBoxRef = useRef<HTMLDivElement>(null);
  const bgColor = useColorModeValue('gray.50', 'gray.900');

  const fetchLogs = async () => {
    try {
      const response = await fetch(`/api/v1/system/logs?service=${selectedService}`);
      const data = await response.json();
      setLogs(data.logs);
      
      // Auto-scroll para o final
      if (logBoxRef.current) {
        logBoxRef.current.scrollTop = logBoxRef.current.scrollHeight;
      }
    } catch (error) {
      console.error('Erro ao buscar logs:', error);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, [selectedService]);

  const downloadLogs = () => {
    const logText = logs.map(log => 
      `[${log.timestamp}] ${log.level}: ${log.message}`
    ).join('\n');
    
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedService}-logs.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <VStack spacing={4} align="stretch">
      <HStack>
        <Select
          value={selectedService}
          onChange={(e) => setSelectedService(e.target.value)}
        >
          <option value="all">Todos os Serviços</option>
          <option value="api">API</option>
          <option value="comfyui">ComfyUI</option>
          <option value="system">Sistema</option>
        </Select>
        <Button
          leftIcon={<RepeatIcon />}
          onClick={fetchLogs}
          colorScheme="blue"
        >
          Atualizar
        </Button>
        <Button
          leftIcon={<DownloadIcon />}
          onClick={downloadLogs}
          colorScheme="green"
        >
          Download
        </Button>
      </HStack>

      <Box
        ref={logBoxRef}
        height="400px"
        overflowY="auto"
        bg={bgColor}
        p={4}
        borderRadius="md"
        fontFamily="mono"
      >
        {logs.map((log, index) => (
          <Text
            key={index}
            color={
              log.level === 'ERROR' ? 'red.500' :
              log.level === 'WARNING' ? 'yellow.500' :
              'inherit'
            }
          >
            <Code>{log.timestamp}</Code> [{log.level}] {log.message}
          </Text>
        ))}
      </Box>
    </VStack>
  );
} 