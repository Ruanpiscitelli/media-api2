@circuit_breaker(
    failure_threshold=5,
    recovery_timeout=60
)
async def comfyui_api_call(prompt):
    # Implementação existente 