"""
Kikamba -> Swahili / English translation.

Kamba does not appear to be one of NLLB-200's covered languages (checked, but
not with full certainty -- re-verify against the actual FLORES-200 language
list if you want to pursue that path as an alternative). This module defaults
to LLM-based translation via the Anthropic API instead, since that's the most
available option for a language this low-resource right now. Expect
inconsistent quality -- Kikamba is low-resource for every model, not just
NLLB's -- and treat this as a placeholder to improve, not a solved problem.
"""
import anthropic

from .config import settings

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def translate(text: str, target_language: str) -> str:
    """target_language: e.g. 'Swahili' or 'English'."""
    if not settings.translation_model:
        raise RuntimeError(
            "TRANSLATION_MODEL not set -- check https://docs.claude.com for "
            "the current model identifier and set it in .env"
        )
    client = _get_client()
    prompt = (
        f"Translate the following Kikamba (Kamba language, Kenya) text into "
        f"{target_language}. Output ONLY the translation, nothing else.\n\n"
        f"Kikamba text: {text}"
    )
    resp = client.messages.create(
        model=settings.translation_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()
