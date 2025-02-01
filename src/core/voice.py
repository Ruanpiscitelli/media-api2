"""
Core classes para gerenciamento e clonagem de vozes.
"""

import os
import json
import asyncio
import torch
from typing import List, Dict, Optional
from datetime import datetime
import uuid
import torch.cuda.amp  # Para mixed precision
from fish_speech.utils.optimizer import create_optimizer
from fish_speech.utils.scheduler import create_scheduler
from fish_speech.utils.cache import ModelCache
from fish_speech.utils.quantization import quantize_model

from src.models.voice import Voice, VoiceCloneRequest, VoiceCloneStatus
from src.utils.storage import save_file, delete_file
from src.utils.gpu import get_available_gpu
from src.config import VOICE_MODELS_DIR, VOICE_SAMPLES_DIR

class VoiceManager:
    """Gerenciador de vozes do sistema."""

    def __init__(self):
        self.voices: Dict[str, Voice] = {}
        self.supported_languages = [
            "en-US", "pt-BR", "ja-JP", "ko-KR", "zh-CN",
            "fr-FR", "de-DE", "ar-SA", "es-ES"
        ]
        self.load_voices()
        self.metrics_cache = {}
        self.translation_model = None
        self.load_translation_model()

    def load_translation_model(self):
        """Carrega o modelo de tradução."""
        from transformers import MarianMTModel, MarianTokenizer
        
        model_name = "Helsinki-NLP/opus-mt-multilingual-en"
        self.translation_model = {
            "model": MarianMTModel.from_pretrained(model_name),
            "tokenizer": MarianTokenizer.from_pretrained(model_name)
        }

    async def translate_text(
        self,
        text: str,
        target_language: str,
        preserve_emphasis: bool = True
    ) -> str:
        """Traduz texto mantendo ênfases e pontuação."""
        if not self.translation_model:
            raise Exception("Modelo de tradução não carregado")
        
        # Preservar ênfases e pontuação
        if preserve_emphasis:
            # Extrair marcações de ênfase
            emphasis_marks = self.extract_emphasis(text)
            text = self.remove_emphasis_marks(text)
        
        # Traduzir
        inputs = self.translation_model["tokenizer"](
            text,
            return_tensors="pt",
            padding=True
        )
        
        outputs = self.translation_model["model"].generate(**inputs)
        translated = self.translation_model["tokenizer"].decode(
            outputs[0],
            skip_special_tokens=True
        )
        
        # Restaurar ênfases
        if preserve_emphasis:
            translated = self.restore_emphasis(translated, emphasis_marks)
        
        return translated

    def extract_emphasis(self, text: str) -> List[Dict]:
        """Extrai marcações de ênfase do texto."""
        import re
        
        emphasis_pattern = r'<emphasis level="(\d+)">(.*?)</emphasis>'
        matches = re.finditer(emphasis_pattern, text)
        
        return [
            {
                "level": match.group(1),
                "text": match.group(2),
                "start": match.start(),
                "end": match.end()
            }
            for match in matches
        ]

    def remove_emphasis_marks(self, text: str) -> str:
        """Remove marcações de ênfase mantendo o texto."""
        import re
        return re.sub(r'<emphasis level="\d+">(.*?)</emphasis>', r'\1', text)

    def restore_emphasis(self, text: str, emphasis_marks: List[Dict]) -> str:
        """Restaura marcações de ênfase no texto traduzido."""
        for mark in emphasis_marks:
            # Encontrar texto traduzido correspondente
            translated_text = self.find_corresponding_text(
                mark["text"],
                text
            )
            if translated_text:
                text = text.replace(
                    translated_text,
                    f'<emphasis level="{mark["level"]}">{translated_text}</emphasis>'
                )
        return text

    def find_corresponding_text(self, original: str, translated: str) -> Optional[str]:
        """Encontra texto correspondente na tradução."""
        # Implementar lógica de correspondência
        # Por exemplo, usando similaridade de strings
        return None  # TODO: Implementar

    async def get_metrics(self, voice_id: str) -> Dict:
        """Obtém métricas de qualidade e performance de uma voz."""
        from pesq import pesq
        from pystoi import stoi
        import numpy as np
        
        # Verificar cache
        if voice_id in self.metrics_cache:
            cached = self.metrics_cache[voice_id]
            if (datetime.now() - cached["timestamp"]).seconds < 3600:
                return cached["metrics"]
        
        voice = self.voices[voice_id]
        
        # Gerar áudio de teste
        test_text = "Este é um texto de teste para avaliação de métricas."
        audio = await self.generate_speech(
            text=test_text,
            voice_id=voice_id
        )
        
        # Calcular métricas
        metrics = {
            "mos": self.calculate_mos(audio["audio"]),
            "pesq": self.calculate_pesq(audio["audio"]),
            "stoi": self.calculate_stoi(audio["audio"]),
            "cer": self.calculate_cer(test_text, audio["audio"]),
            "wer": self.calculate_wer(test_text, audio["audio"]),
            "rtf": self.calculate_rtf(audio["generation_time"]),
            "avg_time": audio["generation_time"],
            "gpu_util": self.get_gpu_utilization(),
            "memory": self.get_memory_usage()
        }
        
        # Atualizar cache
        self.metrics_cache[voice_id] = {
            "metrics": metrics,
            "timestamp": datetime.now()
        }
        
        return metrics

    def calculate_mos(self, audio: np.ndarray) -> float:
        """Calcula Mean Opinion Score."""
        # TODO: Implementar cálculo de MOS
        return 4.2  # Valor exemplo

    def calculate_pesq(self, audio: np.ndarray) -> float:
        """Calcula PESQ score."""
        # TODO: Implementar cálculo de PESQ
        return 3.8  # Valor exemplo

    def calculate_stoi(self, audio: np.ndarray) -> float:
        """Calcula STOI score."""
        # TODO: Implementar cálculo de STOI
        return 0.92  # Valor exemplo

    def calculate_cer(self, text: str, audio: np.ndarray) -> float:
        """Calcula Character Error Rate."""
        # TODO: Implementar cálculo de CER
        return 0.02  # Valor exemplo

    def calculate_wer(self, text: str, audio: np.ndarray) -> float:
        """Calcula Word Error Rate."""
        # TODO: Implementar cálculo de WER
        return 0.02  # Valor exemplo

    def calculate_rtf(self, generation_time: float) -> float:
        """Calcula Real Time Factor."""
        return generation_time / 1.0  # 1 segundo de áudio

    def get_gpu_utilization(self) -> float:
        """Obtém utilização da GPU."""
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetUtilizationRates(handle)
            return info.gpu
        except:
            return 0

    def get_memory_usage(self) -> str:
        """Obtém uso de memória."""
        try:
            import psutil
            mem = psutil.Process().memory_info().rss / 1024 / 1024 / 1024
            return f"{mem:.1f}GB"
        except:
            return "0GB"

    def load_voices(self):
        """Carrega as vozes disponíveis do disco."""
        if not os.path.exists(VOICE_MODELS_DIR):
            os.makedirs(VOICE_MODELS_DIR)
        
        # Carregar vozes pré-definidas
        for voice_dir in os.listdir(VOICE_MODELS_DIR):
            config_path = os.path.join(VOICE_MODELS_DIR, voice_dir, "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                    voice = Voice(**config)
                    self.voices[voice.id] = voice

    async def list_voices(self) -> List[Voice]:
        """Lista todas as vozes disponíveis."""
        return list(self.voices.values())

    async def get_voice(self, voice_id: str) -> Optional[Voice]:
        """Obtém uma voz específica."""
        return self.voices.get(voice_id)

    async def add_voice(self, voice: Voice) -> str:
        """Adiciona uma nova voz ao sistema."""
        voice_id = str(uuid.uuid4())
        voice.id = voice_id
        
        # Criar diretório para a voz
        voice_dir = os.path.join(VOICE_MODELS_DIR, voice_id)
        os.makedirs(voice_dir, exist_ok=True)

        # Salvar configuração
        config_path = os.path.join(voice_dir, "config.json")
        with open(config_path, "w") as f:
            json.dump(voice.dict(), f, indent=4)

        self.voices[voice_id] = voice
        return voice_id

    async def update_voice(self, voice_id: str, updates: Dict) -> Voice:
        """Atualiza uma voz existente."""
        voice = self.voices[voice_id]
        
        for key, value in updates.items():
            setattr(voice, key, value)

        # Atualizar configuração
        config_path = os.path.join(VOICE_MODELS_DIR, voice_id, "config.json")
        with open(config_path, "w") as f:
            json.dump(voice.dict(), f, indent=4)

        return voice

    async def delete_voice(self, voice_id: str):
        """Remove uma voz do sistema."""
        if voice_id in self.voices:
            voice = self.voices[voice_id]
            
            # Remover arquivos
            voice_dir = os.path.join(VOICE_MODELS_DIR, voice_id)
            if os.path.exists(voice_dir):
                for file in os.listdir(voice_dir):
                    file_path = os.path.join(voice_dir, file)
                    os.remove(file_path)
                os.rmdir(voice_dir)

            del self.voices[voice_id]

class VoiceCloner:
    """Gerenciador de clonagem de vozes."""

    def __init__(self):
        self.active_clones: Dict[str, VoiceCloneStatus] = {}
        self.voice_manager = VoiceManager()
        self.model_cache = ModelCache(max_size=5)  # Cache para modelos mais usados
        self.scaler = torch.cuda.amp.GradScaler()  # Para mixed precision training

    async def start_cloning(self, request: VoiceCloneRequest) -> str:
        """Inicia um novo processo de clonagem."""
        clone_id = str(uuid.uuid4())
        
        status = VoiceCloneStatus(
            clone_id=clone_id,
            status="processing",
            progress=0,
            started_at=datetime.now()
        )
        
        self.active_clones[clone_id] = status
        return clone_id

    async def get_status(self, clone_id: str) -> Optional[VoiceCloneStatus]:
        """Obtém o status de um processo de clonagem."""
        return self.active_clones.get(clone_id)

    async def process_cloning(self, clone_id: str):
        """Processa a clonagem de voz em background."""
        try:
            status = self.active_clones[clone_id]
            status.status = "preparing"
            status.progress = 10

            # Obter GPU disponível
            gpu_id = await get_available_gpu()
            if gpu_id is None:
                raise Exception("Nenhuma GPU disponível")

            # Carregar modelo de clonagem
            device = torch.device(f"cuda:{gpu_id}")
            model = self.load_cloning_model(device)

            status.status = "processing"
            status.progress = 30

            # Processar amostras
            clone_request = status.request
            processed_samples = []
            for i, (sample_path, transcription) in enumerate(zip(clone_request.sample_paths, clone_request.transcriptions)):
                # Processar cada amostra
                processed = await self.process_sample(
                    model, 
                    sample_path, 
                    transcription, 
                    device
                )
                processed_samples.append(processed)
                status.progress = 30 + (40 * (i + 1) // len(clone_request.sample_paths))

            # Treinar modelo clonado
            status.status = "training"
            status.progress = 70
            cloned_model = await self.train_cloned_model(
                model,
                processed_samples,
                clone_request.settings,
                device
            )

            # Gerar preview
            status.status = "generating_preview"
            status.progress = 90
            preview_path = await self.generate_preview(
                cloned_model,
                "Olá, esta é uma demonstração da minha voz clonada.",
                device
            )

            # Salvar modelo e criar voz
            voice = Voice(
                name=clone_request.name,
                description=clone_request.description,
                language=clone_request.language,
                gender=clone_request.gender,
                model_path=f"models/voices/{clone_id}/model.pth",
                config_path=f"models/voices/{clone_id}/config.json",
                preview_url=preview_path,
                tags=["cloned"]
            )

            voice_id = await self.voice_manager.add_voice(voice)

            # Atualizar status
            status.status = "completed"
            status.progress = 100
            status.voice_id = voice_id
            status.preview_url = preview_path
            status.completed_at = datetime.now()

        except Exception as e:
            status = self.active_clones[clone_id]
            status.status = "failed"
            status.error = str(e)

    def load_cloning_model(self, device: torch.device):
        """Carrega o modelo base para clonagem com otimizações."""
        from fish_speech.models import FishSpeechModel
        from fish_speech.config import ModelConfig
        
        # Tentar carregar do cache primeiro
        cached_model = self.model_cache.get("base_model")
        if cached_model is not None:
            return cached_model
        
        config = ModelConfig(
            model_name="fish_speech_base",
            sample_rate=24000,
            hop_length=256,
            hidden_channels=256,
            filter_channels=768,
            n_heads=2,
            n_layers=6,
            kernel_size=3,
            p_dropout=0.1,
            resblock=True,
            mean_only=False,
            emotion_embedding=True
        )
        
        model = FishSpeechModel(config)
        model.load_state_dict(torch.load("models/fish_speech_base.pth"))
        
        # Otimizações
        if device.type == "cuda":
            model = model.half()  # FP16 para GPU
            model = torch.compile(model)  # TorchScript compilation
        
        model.to(device)
        model.eval()
        
        # Adicionar ao cache
        self.model_cache.add("base_model", model)
        
        return model

    async def process_sample(
        self,
        model,
        sample_path: str,
        transcription: str,
        device: torch.device
    ):
        """Processa uma amostra de áudio para clonagem."""
        from fish_speech.utils.audio import load_audio, mel_spectrogram
        from fish_speech.utils.text import text_to_sequence
        
        # Carregar e processar áudio
        audio = load_audio(sample_path, sr=24000)
        mel = mel_spectrogram(
            audio, 
            n_fft=2048,
            hop_length=256,
            win_length=1024,
            sampling_rate=24000,
            n_mel_channels=80
        )
        
        # Processar texto
        text = text_to_sequence(transcription)
        
        # Mover para GPU
        mel = torch.FloatTensor(mel).to(device)
        text = torch.LongTensor(text).to(device)
        
        return {
            "mel": mel,
            "text": text,
            "audio": audio
        }

    async def train_cloned_model(
        self,
        base_model,
        processed_samples: List,
        settings: Dict,
        device: torch.device
    ):
        """Treina o modelo clonado com otimizações."""
        from fish_speech.models import FishSpeechModel
        from fish_speech.trainer import Trainer
        from fish_speech.config import TrainingConfig
        
        # Configurações otimizadas
        train_config = TrainingConfig(
            batch_size=8,
            learning_rate=0.0001,
            epochs=50 if settings["quality"] == "high" else 25,
            warmup_steps=1000,
            checkpoint_interval=1000,
            eval_interval=100,
            preserve_pronunciation=settings.get("preserve_pronunciation", True),
            mixed_precision=True,
            gradient_accumulation_steps=4,
            gradient_clipping=1.0
        )
        
        # Criar clone otimizado
        cloned_model = FishSpeechModel(base_model.config)
        cloned_model.load_state_dict(base_model.state_dict())
        
        if device.type == "cuda":
            cloned_model = cloned_model.half()  # FP16
            cloned_model = torch.compile(cloned_model)  # TorchScript
        
        # Otimizador e scheduler otimizados
        optimizer = create_optimizer(
            cloned_model,
            train_config.learning_rate,
            weight_decay=0.01
        )
        scheduler = create_scheduler(
            optimizer,
            train_config.warmup_steps,
            train_config.total_steps
        )
        
        # Preparar dados com cache
        train_data = self.prepare_training_data(
            processed_samples,
            train_config.batch_size
        )
        
        # Treinamento com mixed precision
        trainer = Trainer(
            model=cloned_model,
            train_config=train_config,
            device=device,
            optimizer=optimizer,
            scheduler=scheduler,
            scaler=self.scaler
        )
        
        await trainer.train(train_data)
        
        # Quantização para inferência
        if settings.get("quantize", True):
            cloned_model = quantize_model(cloned_model)
        
        return cloned_model

    def prepare_training_data(self, samples: List, batch_size: int):
        """Prepara dados de treinamento com otimizações."""
        from torch.utils.data import DataLoader, Dataset
        import numpy as np
        
        class VoiceDataset(Dataset):
            def __init__(self, samples):
                self.samples = samples
                self.cache = {}
            
            def __len__(self):
                return len(self.samples)
            
            def __getitem__(self, idx):
                if idx in self.cache:
                    return self.cache[idx]
                
                sample = self.samples[idx]
                processed = {
                    "mel": sample["mel"],
                    "text": sample["text"],
                    "speaker_id": 0
                }
                
                self.cache[idx] = processed
                return processed
        
        dataset = VoiceDataset(samples)
        dataloader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=4,
            pin_memory=True
        )
        
        return dataloader

    async def generate_preview(
        self,
        model,
        text: str,
        device: torch.device
    ) -> str:
        """Gera um áudio de preview com otimizações."""
        from fish_speech.utils.text import text_to_sequence
        from fish_speech.utils.audio import save_audio
        import uuid
        
        # Processamento de texto otimizado
        text_seq = torch.LongTensor(text_to_sequence(text)).to(device)
        
        # Geração otimizada
        with torch.cuda.amp.autocast(), torch.no_grad():
            mel, audio = model.generate(
                text_seq,
                speaker_id=0,
                emotion_id=0,
                noise_scale=0.667,
                length_scale=1.0,
                noise_scale_w=0.8,
                max_len=None
            )
        
        # Processamento de áudio otimizado
        preview_id = str(uuid.uuid4())
        preview_path = f"media/previews/{preview_id}.wav"
        
        # Salvar com compressão
        save_audio(
            audio.cpu().numpy(),
            preview_path,
            sr=24000,
            normalize=True,
            trim_silence=True
        )
        
        return preview_path 