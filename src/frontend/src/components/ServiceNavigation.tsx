import React from 'react';
import {
  HStack,
  Button,
  Link,
  useClipboard,
  useToast
} from '@chakra-ui/react';
import { ExternalLinkIcon, CopyIcon } from '@chakra-ui/icons';

export function ServiceNavigation() {
  const toast = useToast();
  const baseUrl = window.location.hostname;
  
  const services = [
    { name: 'ComfyUI', port: 8188, path: '' },
    { name: 'API Docs', port: 8000, path: '/docs' },
    { name: 'Metrics', port: 8000, path: '/metrics' }
  ];

  const handleCopyUrl = (url: string) => {
    navigator.clipboard.writeText(url);
    toast({
      title: 'URL Copiada',
      description: url,
      status: 'success',
      duration: 2000
    });
  };

  return (
    <HStack spacing={4} wrap="wrap">
      {services.map(({ name, port, path }) => {
        const url = `http://${baseUrl}:${port}${path}`;
        return (
          <HStack key={name}>
            <Link href={url} isExternal>
              <Button rightIcon={<ExternalLinkIcon />} colorScheme="blue" variant="outline">
                {name}
              </Button>
            </Link>
            <Button
              size="sm"
              onClick={() => handleCopyUrl(url)}
              icon={<CopyIcon />}
              variant="ghost"
            />
          </HStack>
        );
      })}
    </HStack>
  );
} 