from src.core.models import ModelType

@router.post("/generate")
async def generate_media(
    model_type: ModelType = Body(...),
    ...
):
    if model_type not in gpu_manager.vram_map:
        raise HTTPException(400, "Model type não suportado")

@router.post("/generate")
async def generate_image(
    request: GenerationRequest = Body(..., examples=...),
    current_user: User = Depends(get_current_user)
):
    validate_request(request)  # Nova função de validação
    check_quota(current_user)
    task = await queue.add_task(request) 