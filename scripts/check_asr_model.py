"""
Run this FIRST, before building or trusting anything else in this repo.

Confirms whether the configured ASR_MODEL_ID (default: facebook/mms-1b-all)
actually has a working adapter for ASR_TARGET_LANG (default: 'kam'). Your own
KambaBench-ASR/README.md claims Kamba is MMS-supported; independent checks
run while building this scaffold could not fully confirm that against this
specific checkpoint (see PLAN.md). This script does the real check, with real
network access to Hugging Face -- trust this result over anything written in
PLAN.md or the README.

Usage (from the kam-backend/ directory):
    python scripts/check_asr_model.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings  # noqa: E402


def main():
    print(f"Model:       {settings.asr_model_id}")
    print(f"Target lang: {settings.asr_target_lang}")
    print("Loading processor (downloads tokenizer/adapter config)...")

    from transformers import AutoProcessor, Wav2Vec2ForCTC

    try:
        processor = AutoProcessor.from_pretrained(
            settings.asr_model_id, target_lang=settings.asr_target_lang
        )
    except Exception as e:
        print(f"\nFAILED to load processor/adapter for '{settings.asr_target_lang}': {e}")
        print(
            "\nThis most likely means this checkpoint does not have a Kamba "
            "adapter. See PLAN.md, 'Fallback if MMS has no Kamba adapter.'"
        )
        sys.exit(1)

    print("Loading model + adapter weights...")
    try:
        model = Wav2Vec2ForCTC.from_pretrained(
            settings.asr_model_id,
            target_lang=settings.asr_target_lang,
            ignore_mismatched_sizes=True,
        )
        model.load_adapter(settings.asr_target_lang)
    except Exception as e:
        print(f"\nFAILED to load model adapter: {e}")
        sys.exit(1)

    vocab_size = len(processor.tokenizer.get_vocab())
    print(
        f"\nSUCCESS: {settings.asr_model_id} has a working "
        f"'{settings.asr_target_lang}' adapter (vocab size: {vocab_size})."
    )
    print("Proceed to: python scripts/test_transcribe.py <a_real_kikamba_clip>")


if __name__ == "__main__":
    main()
