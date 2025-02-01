async def test_comfy_workflow():
    workflow = {
        "nodes": [
            {"type": "CheckpointLoader", "inputs": {"ckpt_name": "sdxl_v1.0"}},
            {"type": "KSampler", "inputs": {"steps": 25}}
        ]
    }
    
    result = await comfy_executor.execute(workflow, gpu_id=0)
    assert "outputs" in result
    assert len(result["images"]) > 0 