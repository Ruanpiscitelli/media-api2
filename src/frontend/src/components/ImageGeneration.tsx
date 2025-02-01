import React, { useState } from 'react';
import {
  VStack,
  HStack,
  Box,
  Textarea,
  Button,
  Image,
  Progress,
  Select,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
} from '@chakra-ui/react';

export function ImageGeneration() {
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const response = await fetch('/api/v1/generate/image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          negative_prompt: negativePrompt,
          model: 'sdxl',
          steps: 30,
          cfg_scale: 7
        })
      });
      
      const data = await response.json();
      setResult(data.image_url);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <VStack spacing={4} align="stretch">
      <Box>
        <Textarea
          placeholder="Enter your prompt here..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          size="lg"
        />
      </Box>

      <Box>
        <Textarea
          placeholder="Negative prompt (optional)"
          value={negativePrompt}
          onChange={(e) => setNegativePrompt(e.target.value)}
          size="md"
        />
      </Box>

      <HStack>
        <Select defaultValue="sdxl">
          <option value="sdxl">Stable Diffusion XL</option>
          <option value="sd15">Stable Diffusion 1.5</option>
        </Select>

        <NumberInput defaultValue={30} min={1} max={150}>
          <NumberInputField />
          <NumberInputStepper>
            <NumberIncrementStepper />
            <NumberDecrementStepper />
          </NumberInputStepper>
        </NumberInput>
      </HStack>

      <Button
        colorScheme="blue"
        onClick={handleGenerate}
        isLoading={generating}
      >
        Generate Image
      </Button>

      {generating && <Progress size="xs" isIndeterminate />}

      {result && (
        <Box borderWidth={1} borderRadius="lg" overflow="hidden">
          <Image src={result} alt="Generated image" />
        </Box>
      )}
    </VStack>
  );
} 