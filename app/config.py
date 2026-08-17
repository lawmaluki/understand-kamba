"""
Central settings, read from environment variables (see .env.example).
Load a .env file yourself (e.g. `python-dotenv`, or your shell) before
starting the app -- this module doesn't do that automatically, to keep it
dependency-light.
"""
import os
from dataclasses import dataclass


@dataclass
class Settings:
    # ASR
    asr_model_id: str = os.getenv("ASR_MODEL_ID", "facebook/mms-1b-all")
    asr_target_lang: str = os.getenv("ASR_TARGET_LANG", "kam")
    max_audio_seconds: int = int(os.getenv("MAX_AUDIO_SECONDS", "60"))
    sample_rate: int = int(os.getenv("SAMPLE_RATE", "16000"))

    # Translation
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    translation_model: str = os.getenv("TRANSLATION_MODEL", "")

    # Server
    upload_max_mb: int = int(os.getenv("UPLOAD_MAX_MB", "25"))
    temp_dir: str = os.getenv("TEMP_DIR", "/tmp/kam-backend")


settings = Settings()
