"""
Kikamba speech-to-text via a CTC model (default: FarmerlineML/w2v-bert-2.0_kamba,
a w2v-BERT 2.0 fine-tune on Kamba -- its card reports ~30% WER / 7% CER on its
own eval set; the training data is undocumented).

Meta's MMS (facebook/mms-1b-all) also works: set ASR_MODEL_ID to it and the
'kam' adapter is loaded. Whether MMS actually ships a Kamba adapter is still
unconfirmed -- run scripts/check_asr_model.py first if you switch to it.
"""
import threading

import soundfile as sf
import torch
from transformers import AutoModelForCTC, AutoProcessor

from .config import settings

_lock = threading.Lock()
_model = None
_processor = None


def _is_mms() -> bool:
    return "mms" in settings.asr_model_id.lower()


def _load():
    """Load model + processor once, lazily, thread-safely."""
    global _model, _processor
    if _model is not None:
        return
    with _lock:
        if _model is not None:
            return
        if _is_mms():
            kwargs = {"target_lang": settings.asr_target_lang}
            processor = AutoProcessor.from_pretrained(settings.asr_model_id, **kwargs)
            model = AutoModelForCTC.from_pretrained(
                settings.asr_model_id, ignore_mismatched_sizes=True, **kwargs
            )
            model.load_adapter(settings.asr_target_lang)
        else:
            processor = AutoProcessor.from_pretrained(settings.asr_model_id)
            model = AutoModelForCTC.from_pretrained(settings.asr_model_id)
        model.eval()
        _processor = processor
        _model = model


def transcribe_wav_file(path: str) -> str:
    """Transcribe a 16kHz mono WAV file (use app.audio.to_wav_16k_mono first
    if the input isn't already in that format)."""
    _load()
    audio, sr = sf.read(path, dtype="float32")
    if sr != settings.sample_rate:
        raise ValueError(
            f"expected {settings.sample_rate}Hz audio, got {sr}Hz — "
            f"run audio.to_wav_16k_mono() first"
        )
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    inputs = _processor(audio, sampling_rate=settings.sample_rate, return_tensors="pt")
    with torch.inference_mode():
        logits = _model(**inputs).logits
    ids = torch.argmax(logits, dim=-1)[0]
    return _processor.decode(ids).strip()
