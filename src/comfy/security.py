class WorkflowValidator:
    ALLOWED_NODES = {
        "KSampler", "CLIPTextEncode", "CheckpointLoader",
        "LoraLoader", "VAEDecode"
    }
    
    def validate(self, workflow):
        for node in workflow["nodes"]:
            if node["type"] not in self.ALLOWED_NODES:
                raise InvalidWorkflowError(f"Node proibido: {node['type']}") 