"""
MMS-based ASR wrapper, targeting Kikamba ('kam').

IMPORTANT -- run scripts/check_asr_model.py BEFORE relying on this module.
It is not yet confirmed that ASR_MODEL_ID (default: facebook/mms-1b-all)
actually ships a working adapter for 'kam'. See PLAN.md, "Open question to
resolve first."
"""
import threading

import soundfile as sf
import torch
from transformers import AutoProcessor, Wav2Vec2ForCTC

from .config import settings

_lock = threading.Lock()
_model = None
_processor = None


def _load():
    """Load model + processor once, lazily, thread-safely. Call this
    explicitly at process startup (see main.py) if you want the first
    request to be fast rather than paying the load cost on it."""
    global _model, _processor
    if _model is not None:
        return
    with _lock:
        if _model is not None:
            return
        processor = AutoProcessor.from_pretrained(
            settings.asr_model_id, target_lang=settings.asr_target_lang
        )
        model = Wav2Vec2ForCTC.from_pretrained(
            settings.asr_model_id,
            target_lang=settings.asr_target_lang,
            ignore_mismatched_sizes=True,
        )
        model.load_adapter(settings.asr_target_lang)
        model.eval()
        _processor = processor
        _model = model


def transcribe_wav_file(path: str) -> str:
    """Transcribe a 16kHz mono WAV file (use app.audio.to_wav_16k_mono first
    if the input isn't already in that format)."""
    _load()
    audio, sr = sf.read(path)
    if sr != settings.sample_rate:
        raise ValueError(
            f"expected {settings.sample_rate}Hz audio, got {sr}Hz — "
            f"run audio.to_wav_16k_mono() first"
        )
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    inputs = _processor(audio, sampling_rate=settings.sample_rate, return_tensors="pt")
    with torch.no_grad():
        logits = _model(**inputs).logits
    ids = torch.argmax(logits, dim=-1)[0]
    return _processor.decode(ids)
