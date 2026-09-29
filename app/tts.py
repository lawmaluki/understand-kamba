"""
Kikamba text-to-speech -- read by Meta's MMS Swahili voice (facebook/mms-tts-swh).

There is no working Kikamba voice model: the only community one found
(Musembi/speecht5-tts-kamba) has NaN weights and outputs silence. Swahili
spelling is close enough to Kikamba that the Swahili voice is intelligible --
round-tripping its output through the Kamba ASR model recovers the text
almost word for word -- but it has a Swahili accent, and since the Swahili
vocabulary has no ĩ/ũ those are read as plain i/u (see _normalize).

Swap TTS_MODEL_ID for any VITS/MMS-TTS model (e.g. a future facebook/mms-tts-kam).
"""
import io
import threading
import unicodedata

import numpy as np
import soundfile as sf
import torch

from .config import settings
from .translate import split_sentences

_lock = threading.Lock()
_model = None
_tokenizer = None


def _load():
    global _model, _tokenizer
    if _model is not None:
        return
    with _lock:
        if _model is not None:
            return
        from transformers import AutoTokenizer, VitsModel

        tokenizer = AutoTokenizer.from_pretrained(settings.tts_model_id)
        model = VitsModel.from_pretrained(settings.tts_model_id)
        model.eval()
        _tokenizer = tokenizer
        _model = model


def _normalize(text: str) -> str:
    # ĩ -> i, ũ -> u, etc.: decompose, then drop the combining marks.
    decomposed = unicodedata.normalize("NFD", text)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(plain.replace("’", "'").lower().split())


def synthesize_wav(text: str) -> bytes:
    """Return mono WAV bytes of `text` read aloud. Sentences are generated
    one at a time with a short pause between them."""
    _load()
    sample_rate = _model.config.sampling_rate
    pause = np.zeros(int(sample_rate * 0.25), dtype=np.float32)
    pieces = []
    for sentence in split_sentences(_normalize(text)):
        inputs = _tokenizer(sentence, return_tensors="pt")
        if inputs["input_ids"].shape[1] == 0:
            continue  # nothing the voice can pronounce (e.g. only punctuation)
        with torch.inference_mode():
            pieces += [_model(**inputs).waveform[0].numpy(), pause]
    if not pieces:
        raise ValueError("nothing to synthesize")

    buf = io.BytesIO()
    sf.write(buf, np.concatenate(pieces[:-1]), sample_rate, format="WAV")
    return buf.getvalue()
