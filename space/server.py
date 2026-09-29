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

The models run on CPU. The one @spaces.GPU function below exists only to
satisfy that startup check and is never called, so visitors never spend
ZeroGPU's small per-visitor daily GPU quota.
"""
import spaces  # noqa: I001 -- must come before torch is imported

import threading

import gradio as gr
import torch

from app import asr, tts
from app import translate as translate_mod
from app.main import app as api
from app.translate import ENGLISH, KIKAMBA


@spaces.GPU(duration=10)
def _gpu_available() -> bool:
    """Never called; see module docstring."""
    return torch.cuda.is_available()


def _warm_up():
    """Load models in the background so the first visitor doesn't wait for downloads."""
    for name, load in [("translation", translate_mod._load_nllb), ("voice", tts._load), ("speech", asr._load)]:
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
