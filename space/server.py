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

Speech, voice and (by default) translation run on CPU. If NLLB_GPU_MODEL_ID
is set (e.g. facebook/nllb-200-3.3B), translation runs that model on the GPU
and falls back to the CPU model (NLLB_MODEL_ID) whenever the GPU can't be
used. API calls from the website carry no visitor token, so ZeroGPU charges
them to one small daily quota shared by the whole Space; once it's used up,
the CPU model serves until the quota resets.
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
