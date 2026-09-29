"""
Kikamba <-> Swahili / English translation.

Two backends:
  - "nllb" (default): Meta's NLLB-200 model, run locally via transformers.
    Free, no API key needed. IMPORTANT: contrary to this module's earlier
    assumption, NLLB-200 *does* ship a Kamba code ('kam_Latn') -- confirmed
    by loading facebook/nllb-200-distilled-600M's tokenizer directly. But
    Kamba is still low-resource in NLLB's training data, and its output has
    been observed to carry grammatical markers characteristic of Kikuyu (a
    closely related language) -- treat quality as unverified, not solved.
  - "anthropic": LLM-based translation via the Anthropic API. Needs
    ANTHROPIC_API_KEY + TRANSLATION_MODEL. Was the only backend before NLLB
    support was added; kept as an alternative for when translation quality
    needs improving beyond what NLLB gives for free.

Select with TRANSLATION_BACKEND in .env ("nllb" or "anthropic").
"""
import re
import threading

from .config import settings

# Language names double as the wording in the Anthropic prompt, hence the
# disambiguating "(Kamba language, Kenya)".
KIKAMBA = "Kikamba (Kamba language, Kenya)"
ENGLISH = "English"
SWAHILI = "Swahili"

# FLORES-200 codes NLLB expects. Extend this if more languages are needed.
_NLLB_LANG_CODES = {
    KIKAMBA: "kam_Latn",
    ENGLISH: "eng_Latn",
    SWAHILI: "swh_Latn",
}

_nllb_lock = threading.Lock()
_nllb_model = None
_nllb_tokenizer = None


def _load_nllb():
    global _nllb_model, _nllb_tokenizer
    if _nllb_model is not None:
        return
    with _nllb_lock:
        if _nllb_model is not None:
            return
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        _nllb_tokenizer = AutoTokenizer.from_pretrained(settings.nllb_model_id)
        _nllb_model = AutoModelForSeq2SeqLM.from_pretrained(settings.nllb_model_id)
        _nllb_model.eval()


# Split after sentence-final punctuation followed by whitespace. NLLB is
# trained on single sentences; feeding it a paragraph makes it drop or
# hallucinate clauses, so each sentence is translated on its own.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]


def _nllb_translate(text: str, source_language: str, target_language: str) -> str:
    if source_language not in _NLLB_LANG_CODES or target_language not in _NLLB_LANG_CODES:
        raise ValueError(
            f"no NLLB language code known for {source_language!r} -> "
            f"{target_language!r}; add it to _NLLB_LANG_CODES in translate.py"
        )
    sentences = split_sentences(text)
    if not sentences:
        return ""

    import torch

    _load_nllb()
    with _nllb_lock:  # tokenizer.src_lang is shared mutable state
        _nllb_tokenizer.src_lang = _NLLB_LANG_CODES[source_language]
        inputs = _nllb_tokenizer(sentences, return_tensors="pt", padding=True)
    tgt_id = _nllb_tokenizer.convert_tokens_to_ids(_NLLB_LANG_CODES[target_language])
    # Cap output relative to input so the model can't run on and invent text.
    max_new_tokens = int(inputs["input_ids"].shape[1] * 2) + 16
    with torch.inference_mode():
        out = _nllb_model.generate(
            **inputs,
            forced_bos_token_id=tgt_id,
            num_beams=settings.nllb_num_beams,
            max_new_tokens=max_new_tokens,
            no_repeat_ngram_size=4,
        )
    decoded = _nllb_tokenizer.batch_decode(out, skip_special_tokens=True)
    return " ".join(d.strip() for d in decoded)


_anthropic_client = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic

        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        _anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


def _anthropic_translate(text: str, source_language: str, target_language: str) -> str:
    if not settings.translation_model:
        raise RuntimeError(
            "TRANSLATION_MODEL not set -- check https://docs.claude.com for "
            "the current model identifier and set it in .env"
        )
    client = _get_anthropic_client()
    prompt = (
        f"Translate the following {source_language} text into "
        f"{target_language}. Output ONLY the translation, nothing else.\n\n"
        f"{source_language} text: {text}"
    )
    resp = client.messages.create(
        model=settings.translation_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


def translate(text: str, target_language: str, source_language: str = KIKAMBA) -> str:
    """Languages are the KIKAMBA / ENGLISH / SWAHILI constants above.
    Defaults to Kikamba -> target; pass source_language=ENGLISH for the
    reverse direction. Backend (NLLB, local + free, or Anthropic,
    API-key-based) is chosen by TRANSLATION_BACKEND in .env."""
    if settings.translation_backend == "anthropic":
        return _anthropic_translate(text, source_language, target_language)
    return _nllb_translate(text, source_language, target_language)


def translation_available() -> bool:
    """Whether the configured backend is actually usable right now."""
    if settings.translation_backend == "anthropic":
        return bool(settings.anthropic_api_key and settings.translation_model)
    return True
