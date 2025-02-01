async def verify_model_signature(model_path):
    expected_hash = {
        "SDXL": "a1b2c3d4e5f6...",
        "FishSpeech": "f6e5d4c3b2a1..."
    }
    
    model_name = Path(model_path).stem
    current_hash = calculate_file_hash(model_path)
    
    if expected_hash.get(model_name) != current_hash:
        raise SecurityError("Model hash mismatch") 