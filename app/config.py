"""
Central settings, read from environment variables (see .env.example).
Load a .env file yourself (e.g. `python-dotenv`, or your shell) before
starting the app -- this module doesn't do that automatically, to keep it
dependency-light.
"""
import os
import tempfile
from dataclasses import dataclass


@dataclass
class Settings:
    # ASR
    asr_model_id: str = os.getenv("ASR_MODEL_ID", "FarmerlineML/w2v-bert-2.0_kamba")
    asr_target_lang: str = os.getenv("ASR_TARGET_LANG", "kam")  # MMS adapter only

    # Text-to-speech (see app/tts.py for why this is a Swahili voice)
    tts_model_id: str = os.getenv("TTS_MODEL_ID", "facebook/mms-tts-swh")

    # Where translation counts and user ratings are kept (see app/stats.py).
    data_dir: str = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))

    # Voice-recording contributions (see app/voice.py). With VOICE_DATASET_REPO
    # set (e.g. "lawmaluki/kamba-voice-recordings") recordings are pushed to
    # that private Hugging Face dataset, using the HF_TOKEN environment
    # variable; otherwise they're only kept locally under data/voice.
    voice_dataset_repo: str = os.getenv("VOICE_DATASET_REPO", "")
    voice_max_seconds: int = int(os.getenv("VOICE_MAX_SECONDS", "20"))
    voice_upload_max_mb: int = int(os.getenv("VOICE_UPLOAD_MAX_MB", "5"))
    voice_uploads_per_hour: int = int(os.getenv("VOICE_UPLOADS_PER_HOUR", "120"))
    # Translation corrections suggested by users (see app/corrections.py). Pushed
    # to this private dataset; defaults to <voice dataset owner>/kamba-translation-corrections.
    corrections_dataset_repo: str = os.getenv(
        "CORRECTIONS_DATASET_REPO",
        f"{voice_dataset_repo.split('/')[0]}/kamba-translation-corrections" if "/" in voice_dataset_repo else "",
    )
    corrections_per_hour: int = int(os.getenv("CORRECTIONS_PER_HOUR", "60"))
    # Per-visitor hourly limits on the expensive routes (app/ratelimit.py); 0 = no limit.
    # Generous for people, but stop one visitor or bot using up the shared GPU quota.
    translate_per_hour: int = int(os.getenv("TRANSLATE_PER_HOUR", "200"))
    suggestions_per_hour: int = int(os.getenv("SUGGESTIONS_PER_HOUR", "60"))
    synthesize_per_hour: int = int(os.getenv("SYNTHESIZE_PER_HOUR", "100"))
    transcribe_per_hour: int = int(os.getenv("TRANSCRIBE_PER_HOUR", "60"))
    # Usage counts and ratings (see app/stats.py), synced to this private dataset so they
    # survive restarts; defaults to <voice dataset owner>/kamba-app-stats. Empty = local only.
    stats_dataset_repo: str = os.getenv(
        "STATS_DATASET_REPO",
        f"{voice_dataset_repo.split('/')[0]}/kamba-app-stats" if "/" in voice_dataset_repo else "",
    )
    max_audio_seconds: int = int(os.getenv("MAX_AUDIO_SECONDS", "60"))
    sample_rate: int = int(os.getenv("SAMPLE_RATE", "16000"))

    # Translation
    translation_backend: str = os.getenv("TRANSLATION_BACKEND", "nllb")  # "nllb" or "anthropic"
    nllb_model_id: str = os.getenv("NLLB_MODEL_ID", "facebook/nllb-200-distilled-600M")
    nllb_num_beams: int = int(os.getenv("NLLB_NUM_BEAMS", "5"))
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    translation_model: str = os.getenv("TRANSLATION_MODEL", "")
    # Keep in sync with MAX_CHARS in web/src/components/translator/ContentArea.tsx.
    max_translate_chars: int = int(os.getenv("MAX_TRANSLATE_CHARS", "500"))

    # Server
    upload_max_mb: int = int(os.getenv("UPLOAD_MAX_MB", "25"))
    temp_dir: str = os.getenv("TEMP_DIR", os.path.join(tempfile.gettempdir(), "kam-backend"))


settings = Settings()
