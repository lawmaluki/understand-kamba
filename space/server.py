"""
Hugging Face Space entry point (Gradio SDK on ZeroGPU hardware).

Serves the FastAPI backend's routes (app/main.py: /translate, /transcribe,
/synthesize, /stats, /feedback, /health, /docs) on Gradio's own server,
plus a small Gradio test page at "/".

ZeroGPU rules this file follows:
- `spaces` is imported before anything that imports torch.
- The app starts via demo.launch() -- that is where `spaces` reports the
  app's @spaces.GPU functions to the platform, which refuses to start an app
  that declares none.
- GPU models are moved to "cuda" at module level (ZeroGPU emulates CUDA
  outside @spaces.GPU functions and attaches a real GPU inside them).

Speech-to-text runs on CPU. Two optional GPU models, each with a CPU fallback
used whenever the GPU can't be (e.g. quota used up):
- NLLB_GPU_MODEL_ID (e.g. facebook/nllb-200-3.3B) for translation; fallback
  NLLB_MODEL_ID on CPU.
- TTS_GPU_MODEL_ID (k2-fsa/OmniVoice) for the voice, cloning the Kamba
  speakers in app/data/voices; fallback the Swahili MMS voice (TTS_MODEL_ID).
API calls from the website carry no visitor token, so ZeroGPU charges them
to one small daily quota shared by the whole Space; once it's used up, the
CPU fallbacks serve until the quota resets.
"""
import spaces  # noqa: I001 -- must come before torch is imported

import os
import threading

import gradio as gr
import torch

from app import asr, tts
from app import translate as translate_mod
from app.main import app as api
from app.translate import ENGLISH, KIKAMBA

GPU_MODEL_ID = os.getenv("NLLB_GPU_MODEL_ID", "")


@spaces.GPU(duration=10)
def _gpu_available() -> bool:
    """Never called. Guarantees ZeroGPU's startup check finds a GPU function."""
    return torch.cuda.is_available()


if GPU_MODEL_ID:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    _gpu_tokenizer = AutoTokenizer.from_pretrained(GPU_MODEL_ID)
    # float16 halves memory (3.3B: ~7 GB instead of ~13 GB) with no practical quality loss on GPU.
    _gpu_model = AutoModelForSeq2SeqLM.from_pretrained(GPU_MODEL_ID, torch_dtype=torch.float16).to("cuda").eval()

    # duration is the most GPU time a call may use; ZeroGPU only starts it if
    # that much quota is left, so keep it small (a few sentences take ~1-2 s).
    @spaces.GPU(duration=15)
    def _translate_on_gpu(sentences: list[str], src_code: str, tgt_code: str) -> list[str]:
        return translate_mod.nllb_generate(_gpu_model, _gpu_tokenizer, sentences, src_code, tgt_code, device="cuda")

    translate_mod.set_accelerator(_translate_on_gpu, GPU_MODEL_ID)
    print(f"[startup] translation on GPU: {GPU_MODEL_ID} (CPU fallback loads on first use)", flush=True)


TTS_GPU_MODEL_ID = os.getenv("TTS_GPU_MODEL_ID", "")
VOICES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "data", "voices")

if TTS_GPU_MODEL_ID:
    import io

    import numpy as np
    import soundfile as sf
    from omnivoice import OmniVoice

    from app.translate import split_sentences

    _omni = OmniVoice.from_pretrained(TTS_GPU_MODEL_ID)
    # Clone prompts for the two Kamba reference speakers (app/data/voices), built
    # on CPU now because real GPU work can only happen inside @spaces.GPU calls.
    _voice_prompts = {}
    for _voice in tts.VOICES:
        _samples, _sr = sf.read(os.path.join(VOICES_DIR, f"kamba_{_voice}.wav"), dtype="float32")
        with open(os.path.join(VOICES_DIR, f"kamba_{_voice}.txt"), encoding="utf-8") as _f:
            _ref_text = _f.read().strip()
        _voice_prompts[_voice] = _omni.create_voice_clone_prompt((torch.from_numpy(_samples).unsqueeze(0), _sr), _ref_text)
    # Stay in float32: casting the loaded model to float16 makes it output silence
    # (some of its modules need full precision). 0.6B params is ~2.4 GB on the GPU.
    _omni = _omni.to("cuda")
    _SAMPLE_RATE = 24000

    def _speech_duration(sentences: list[str], voice: str) -> int:
        """GPU seconds to reserve: ZeroGPU only starts a call if this much quota
        is left, so scale it with the text instead of always asking for a lot."""
        return min(60, 10 + sum(len(s) for s in sentences) // 15)

    @spaces.GPU(duration=_speech_duration)
    def _speak_on_gpu(sentences: list[str], voice: str) -> list[np.ndarray]:
        n = len(sentences)
        audios = _omni.generate(text=sentences, language=["kam"] * n, voice_clone_prompt=[_voice_prompts[voice]] * n)
        return [np.asarray(a, dtype=np.float32) for a in audios]

    def _speak(text: str, voice: str) -> bytes:
        sentences = split_sentences(text) or [text]
        pause = np.zeros(int(_SAMPLE_RATE * 0.25), dtype=np.float32)
        pieces = [x for audio in _speak_on_gpu(sentences, voice) for x in (audio, pause)][:-1]
        buf = io.BytesIO()
        sf.write(buf, np.concatenate(pieces), _SAMPLE_RATE, format="WAV")
        return buf.getvalue()

    tts.set_accelerator(_speak, TTS_GPU_MODEL_ID)
    print(f"[startup] voice on GPU: {TTS_GPU_MODEL_ID} cloning {list(_voice_prompts)} (fallback: Swahili MMS)", flush=True)


def _warm_up():
    """Load models in the background so the first visitor doesn't wait for downloads.
    With a GPU translation model the CPU one is only a fallback, so it's left to
    load on first use to save memory."""
    loads = [("voice", tts._load), ("speech", asr._load)]
    if not GPU_MODEL_ID:
        loads.insert(0, ("translation", translate_mod._load_nllb))
    for name, load in loads:
        try:
            load()
            print(f"[warm-up] {name} model loaded", flush=True)
        except Exception as e:  # keep serving; the request that needs it will report the error
            print(f"[warm-up] {name} model failed to load: {e}", flush=True)


def _translate(text: str, direction: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if direction == "English → Kikamba":
        return translate_mod.translate(text, KIKAMBA, source_language=ENGLISH)
    return translate_mod.translate(text, ENGLISH)


with gr.Blocks(title="Understand Kamba API") as demo:
    gr.Markdown(
        "# Understand Kamba API\n"
        "Backend for the Understand Kamba translator. Try a translation below. The web app calls "
        "`/translate`, `/transcribe`, `/synthesize`, `/stats` and `/feedback`; see `/docs`."
    )
    direction = gr.Radio(["English → Kikamba", "Kikamba → English"], value="English → Kikamba", label="Direction")
    source = gr.Textbox(label="Text", lines=3, value="Good morning, my friend.")
    output = gr.Textbox(label="Translation", lines=3)
    gr.Button("Translate", variant="primary").click(_translate, [source, direction], output, api_name=False)


if __name__ == "__main__":
    threading.Thread(target=_warm_up, daemon=True).start()
    # ssr_mode=False: on Spaces, Gradio otherwise puts a Node.js server-side
    # rendering server in front on port 7860 that only forwards Gradio's own
    # paths, so POST /translate etc. would never reach Python.
    demo.launch(prevent_thread_lock=True, ssr_mode=False)
    # Serve the backend's routes on Gradio's server. None of them clash with
    # Gradio's own paths. Gradio's CORS handling allows any origin when served
    # from a public host, so the Vercel site can call these.
    demo.app.router.routes.extend(api.router.routes)
    demo.block_thread()
