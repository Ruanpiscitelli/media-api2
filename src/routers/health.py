@router.get("/health")
async def health_check():
    checks = {
        "redis": await check_redis(),
        "gpu_available": gpu_manager.has_available_gpu(),
        "comfyui": await check_comfyui()
    }
    return checks 