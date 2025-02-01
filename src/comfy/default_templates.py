"""
Templates padrão do sistema para geração de mídia.
"""
from typing import Dict, Any, List
from datetime import datetime

def get_portrait_template() -> Dict[str, Any]:
    """Template otimizado para geração de retratos com SDXL."""
    return {
        "name": "sdxl-portrait",
        "description": "Template otimizado para geração de retratos com SDXL",
        "workflow": {
            "nodes": {
                "1": {
                    "class_type": "SDXLPromptEncoder",
                    "inputs": {
                        "text_positive": "${prompt}",
                        "text_negative": "${negative_prompt}",
                        "style": "${style}"
                    }
                },
                "2": {
                    "class_type": "KSampler",
                    "inputs": {
                        "seed": "${seed}",
                        "steps": "${steps}",
                        "cfg": "${cfg}",
                        "sampler_name": "${sampler}",
                        "scheduler": "${scheduler}",
                        "denoise": "${denoise}"
                    }
                },
                "3": {
                    "class_type": "SDXLRefiner",
                    "inputs": {
                        "upscale_factor": "${upscale}",
                        "strength": "${refiner_strength}"
                    }
                }
            }
        },
        "parameters": {
            "prompt": {
                "name": "Prompt",
                "type": "string",
                "description": "Prompt principal",
                "default": "portrait of a person, highly detailed, photorealistic",
                "required": True
            },
            "negative_prompt": {
                "name": "Negative Prompt",
                "type": "string",
                "description": "Prompt negativo",
                "default": "blurry, low quality, distorted"
            },
            "seed": {
                "name": "Seed",
                "type": "integer",
                "description": "Seed para geração",
                "default": 123456
            },
            "steps": {
                "name": "Steps",
                "type": "integer",
                "description": "Número de steps",
                "default": 30,
                "min_value": 1,
                "max_value": 100
            },
            "cfg": {
                "name": "CFG Scale",
                "type": "float", 
                "description": "CFG Scale",
                "default": 7.5,
                "min_value": 1.0,
                "max_value": 20.0
            },
            "sampler": {
                "name": "Sampler",
                "type": "enum",
                "description": "Algoritmo de sampling",
                "default": "euler_a",
                "enum_values": [
                    "euler_a",
                    "euler",
                    "dpm++_2m",
                    "ddim"
                ]
            },
            "style": {
                "name": "Estilo",
                "type": "enum",
                "description": "Estilo do retrato",
                "default": "photographic",
                "enum_values": [
                    "photographic",
                    "anime",
                    "artistic",
                    "cinematic"
                ]
            },
            "scheduler": {
                "name": "Scheduler",
                "type": "enum",
                "description": "Tipo de scheduler",
                "default": "karras",
                "enum_values": [
                    "karras",
                    "normal",
                    "simple"
                ]
            },
            "denoise": {
                "name": "Denoise Strength",
                "type": "float",
                "description": "Força do denoising",
                "default": 0.7,
                "min_value": 0.0,
                "max_value": 1.0
            },
            "upscale": {
                "name": "Upscale Factor",
                "type": "float",
                "description": "Fator de upscale",
                "default": 1.5,
                "min_value": 1.0,
                "max_value": 4.0
            },
            "refiner_strength": {
                "name": "Refiner Strength",
                "type": "float",
                "description": "Força do refinamento",
                "default": 0.3,
                "min_value": 0.0,
                "max_value": 1.0
            }
        },
        "parameter_mappings": {
            "prompt": ["1.text_positive"],
            "negative_prompt": ["1.text_negative"],
            "style": ["1.style"],
            "seed": ["2.seed"],
            "steps": ["2.steps"],
            "cfg": ["2.cfg"],
            "sampler": ["2.sampler_name"],
            "scheduler": ["2.scheduler"],
            "denoise": ["2.denoise"],
            "upscale": ["3.upscale_factor"],
            "refiner_strength": ["3.strength"]
        },
        "tags": ["portrait", "sdxl", "photo"],
        "category": "portraits"
    }

def get_landscape_template() -> Dict[str, Any]:
    """Template otimizado para geração de paisagens."""
    return {
        "name": "sdxl-landscape",
        "description": "Template otimizado para geração de paisagens com SDXL",
        "workflow": {
            "nodes": {
                "1": {
                    "class_type": "SDXLPromptEncoder",
                    "inputs": {
                        "text_positive": "${prompt}",
                        "text_negative": "${negative_prompt}",
                        "style": "${style}"
                    }
                },
                "2": {
                    "class_type": "KSampler",
                    "inputs": {
                        "seed": "${seed}",
                        "steps": "${steps}",
                        "cfg": "${cfg}",
                        "sampler_name": "${sampler}",
                        "width": "${width}",
                        "height": "${height}"
                    }
                },
                "3": {
                    "class_type": "UpscaleImage",
                    "inputs": {
                        "upscale_factor": "${upscale}",
                        "upscaler_name": "${upscaler}"
                    }
                }
            }
        },
        "parameters": {
            "prompt": {
                "name": "Prompt",
                "type": "string",
                "description": "Prompt principal",
                "default": "beautiful landscape, nature, mountains, 8k uhd",
                "required": True
            },
            "negative_prompt": {
                "name": "Negative Prompt",
                "type": "string",
                "description": "Prompt negativo",
                "default": "blurry, low quality, text, watermark"
            },
            "seed": {
                "name": "Seed",
                "type": "integer",
                "description": "Seed para geração",
                "default": 123456
            },
            "steps": {
                "name": "Steps",
                "type": "integer",
                "description": "Número de steps",
                "default": 30,
                "min_value": 1,
                "max_value": 100
            },
            "cfg": {
                "name": "CFG Scale",
                "type": "float",
                "description": "CFG Scale",
                "default": 7.5,
                "min_value": 1.0,
                "max_value": 20.0
            },
            "width": {
                "name": "Width",
                "type": "integer",
                "description": "Largura da imagem",
                "default": 1024,
                "enum_values": [768, 1024, 1280]
            },
            "height": {
                "name": "Height", 
                "type": "integer",
                "description": "Altura da imagem",
                "default": 576,
                "enum_values": [576, 768, 1024]
            },
            "style": {
                "name": "Estilo",
                "type": "enum",
                "description": "Estilo da paisagem",
                "default": "photographic",
                "enum_values": [
                    "photographic",
                    "artistic",
                    "cinematic",
                    "fantasy"
                ]
            },
            "upscale": {
                "name": "Upscale Factor",
                "type": "float",
                "description": "Fator de upscale",
                "default": 2.0,
                "min_value": 1.0,
                "max_value": 4.0
            },
            "upscaler": {
                "name": "Upscaler",
                "type": "enum",
                "description": "Método de upscale",
                "default": "RealESRGAN_x4plus",
                "enum_values": [
                    "RealESRGAN_x4plus",
                    "RealESRGAN_x2plus",
                    "SwinIR_4x"
                ]
            }
        },
        "parameter_mappings": {
            "prompt": ["1.text_positive"],
            "negative_prompt": ["1.text_negative"],
            "style": ["1.style"],
            "seed": ["2.seed"],
            "steps": ["2.steps"],
            "cfg": ["2.cfg"],
            "sampler": ["2.sampler_name"],
            "width": ["2.width"],
            "height": ["2.height"],
            "upscale": ["3.upscale_factor"],
            "upscaler": ["3.upscaler_name"]
        },
        "tags": ["landscape", "nature", "sdxl"],
        "category": "landscapes"
    }

def get_concept_art_template() -> Dict[str, Any]:
    """Template para geração de arte conceitual."""
    return {
        "name": "sdxl-concept-art",
        "description": "Template para geração de arte conceitual com SDXL",
        "workflow": {
            "nodes": {
                "1": {
                    "class_type": "SDXLPromptEncoder",
                    "inputs": {
                        "text_positive": "${prompt}",
                        "text_negative": "${negative_prompt}",
                        "style": "${style}"
                    }
                },
                "2": {
                    "class_type": "KSampler",
                    "inputs": {
                        "seed": "${seed}",
                        "steps": "${steps}",
                        "cfg": "${cfg}",
                        "sampler_name": "${sampler}"
                    }
                },
                "3": {
                    "class_type": "ImageProcessor",
                    "inputs": {
                        "sharpness": "${sharpness}",
                        "contrast": "${contrast}",
                        "saturation": "${saturation}"
                    }
                }
            }
        },
        "parameters": {
            "prompt": {
                "name": "Prompt",
                "type": "string",
                "description": "Prompt principal",
                "default": "concept art, fantasy scene, highly detailed",
                "required": True
            },
            "negative_prompt": {
                "name": "Negative Prompt",
                "type": "string",
                "description": "Prompt negativo",
                "default": "blurry, low quality, text, watermark"
            },
            "seed": {
                "name": "Seed",
                "type": "integer",
                "description": "Seed para geração",
                "default": 123456
            },
            "steps": {
                "name": "Steps",
                "type": "integer",
                "description": "Número de steps",
                "default": 30,
                "min_value": 1,
                "max_value": 100
            },
            "cfg": {
                "name": "CFG Scale",
                "type": "float",
                "description": "CFG Scale",
                "default": 7.5,
                "min_value": 1.0,
                "max_value": 20.0
            },
            "style": {
                "name": "Estilo",
                "type": "enum",
                "description": "Estilo artístico",
                "default": "fantasy",
                "enum_values": [
                    "fantasy",
                    "sci-fi",
                    "steampunk",
                    "cyberpunk"
                ]
            },
            "sharpness": {
                "name": "Sharpness",
                "type": "float",
                "description": "Nitidez da imagem",
                "default": 1.5,
                "min_value": 0.0,
                "max_value": 3.0
            },
            "contrast": {
                "name": "Contrast",
                "type": "float",
                "description": "Contraste da imagem",
                "default": 1.2,
                "min_value": 0.0,
                "max_value": 3.0
            },
            "saturation": {
                "name": "Saturation",
                "type": "float",
                "description": "Saturação da imagem",
                "default": 1.1,
                "min_value": 0.0,
                "max_value": 3.0
            }
        },
        "parameter_mappings": {
            "prompt": ["1.text_positive"],
            "negative_prompt": ["1.text_negative"],
            "style": ["1.style"],
            "seed": ["2.seed"],
            "steps": ["2.steps"],
            "cfg": ["2.cfg"],
            "sampler": ["2.sampler_name"],
            "sharpness": ["3.sharpness"],
            "contrast": ["3.contrast"],
            "saturation": ["3.saturation"]
        },
        "tags": ["concept-art", "fantasy", "sdxl"],
        "category": "concept-art"
    }

def get_default_templates() -> List[Dict[str, Any]]:
    """Retorna lista com todos os templates padrão."""
    return [
        get_portrait_template(),
        get_landscape_template(),
        get_concept_art_template()
    ] 