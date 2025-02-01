import re
from typing import Dict, List, Optional

class EndpointParser:
    def __init__(self, markdown_content: str):
        self.content = markdown_content
        self.sections = {}

    def parse(self) -> Dict:
        """Parse o conteúdo markdown e retorne as seções com seus endpoints."""
        current_section = None
        current_endpoint = None
        
        # Regex patterns
        section_pattern = r'^## ([🔑🎨🖼️🎥🗣️🔧📝🎬🖼️📋🔔🛠️📊]?\s*.+)$'
        endpoint_pattern = r'^### (.+)$'
        http_pattern = r'^```http\n(.*?)```'
        json_pattern = r'^```json\n(.*?)```'
        
        lines = self.content.split('\n')
        
        for i, line in enumerate(lines):
            # Encontrar seção
            section_match = re.match(section_pattern, line)
            if section_match:
                section_name = section_match.group(1).strip()
                current_section = {
                    'title': section_name,
                    'description': '',
                    'endpoints': []
                }
                self.sections[self._normalize_section_name(section_name)] = current_section
                continue
                
            # Encontrar endpoint
            endpoint_match = re.match(endpoint_pattern, line)
            if endpoint_match and current_section:
                if current_endpoint:
                    current_section['endpoints'].append(current_endpoint)
                    
                current_endpoint = {
                    'title': endpoint_match.group(1),
                    'method': '',
                    'path': '',
                    'description': '',
                    'curl_example': '',
                    'request_body': '',
                    'response_example': ''
                }
                continue
                
            # Encontrar requisição HTTP
            if '```http' in line and current_endpoint:
                http_block = ''
                j = i + 1
                while j < len(lines) and '```' not in lines[j]:
                    http_block += lines[j] + '\n'
                    j += 1
                    
                # Extrair método e path
                http_parts = http_block.split('\n')[0].split(' ')
                if len(http_parts) >= 2:
                    current_endpoint['method'] = http_parts[0]
                    current_endpoint['path'] = http_parts[1]
                    current_endpoint['curl_example'] = self._generate_curl(http_block)
                continue
                
            # Encontrar exemplo de resposta JSON
            if '```json' in line and current_endpoint:
                json_block = ''
                j = i + 1
                while j < len(lines) and '```' not in lines[j]:
                    json_block += lines[j] + '\n'
                    j += 1
                current_endpoint['response_example'] = json_block
                continue
                
        # Adicionar último endpoint
        if current_endpoint and current_section:
            current_section['endpoints'].append(current_endpoint)
            
        return self.sections
    
    def _normalize_section_name(self, section_name: str) -> str:
        """Normaliza o nome da seção para uso em URLs."""
        # Remover emojis e caracteres especiais
        clean_name = re.sub(r'[^\w\s-]', '', section_name)
        # Converter para lowercase e substituir espaços por hífens
        return clean_name.lower().strip().replace(' ', '-')
    
    def _generate_curl(self, http_block: str) -> str:
        """Gera comando curl a partir do bloco HTTP."""
        lines = http_block.strip().split('\n')
        if not lines:
            return ''
            
        # Primeira linha contém método e path
        first_line = lines[0].split(' ')
        method = first_line[0]
        path = first_line[1]
        
        curl = f"curl -X {method} http://localhost:8000{path}"
        
        # Adicionar headers
        headers = {}
        body = None
        
        for line in lines[1:]:
            if line.startswith('Content-Type:'):
                headers['Content-Type'] = line.split(': ')[1]
            elif line.startswith('Authorization:'):
                headers['Authorization'] = line.split(': ')[1]
            elif line and not line.startswith('{'):
                continue
            elif line.startswith('{'):
                body = line
                
        # Adicionar headers ao comando
        for key, value in headers.items():
            curl += f" \\\n  -H \"{key}: {value}\""
            
        # Adicionar body se existir
        if body:
            curl += f" \\\n  -d '{body}'"
            
        return curl 