import React from 'react';
import {
  ChakraProvider,
  Box,
  VStack,
  HStack,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Text,
  Divider
} from '@chakra-ui/react';

import { ImageGeneration } from './components/ImageGeneration';
import { ModelManager } from './components/ModelManager';
import { SystemStatus } from './components/SystemStatus';
import { ServiceNavigation } from './components/ServiceNavigation';
import { LogViewer } from './components/LogViewer';

function App() {
  return (
    <ChakraProvider>
      <Box p={5}>
        <VStack spacing={5} align="stretch">
          <HStack justify="space-between" wrap="wrap">
            <Text fontSize="2xl" fontWeight="bold">Media Generation Dashboard</Text>
            <SystemStatus />
          </HStack>

          <ServiceNavigation />
          <Divider />

          <Tabs>
            <TabList>
              <Tab>Image Generation</Tab>
              <Tab>Models</Tab>
              <Tab>System Logs</Tab>
            </TabList>

            <TabPanels>
              <TabPanel>
                <ImageGeneration />
              </TabPanel>
              <TabPanel>
                <ModelManager />
              </TabPanel>
              <TabPanel>
                <LogViewer />
              </TabPanel>
            </TabPanels>
          </Tabs>
        </VStack>
      </Box>
    </ChakraProvider>
  );
}

export default App; 