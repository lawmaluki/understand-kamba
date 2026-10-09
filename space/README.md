---
title: Understand Kamba API
emoji: 🗣️
colorFrom: yellow
colorTo: gray
sdk: gradio
sdk_version: 6.28.0
python_version: "3.12"
app_file: server.py
pinned: false
license: cc-by-nc-4.0
short_description: Kikamba translation, speech-to-text and voice API
---

# Understand Kamba API

Backend for the [Understand Kamba](https://understand-kamba.vercel.app) English ⇄ Kikamba
translator. Source: https://github.com/lawmaluki/understand-kamba

| Endpoint | Does | Model |
|---|---|---|
| `POST /translate` | English ⇄ Kikamba; the response's `model` field says which model answered | `facebook/nllb-200-3.3B` on ZeroGPU; falls back to `facebook/nllb-200-distilled-1.3B` on CPU when the GPU quota is used up |
| `POST /transcribe` | Kikamba speech → text | `FarmerlineML/w2v-bert-2.0_kamba` (CPU) |
| `POST /synthesize` | Kikamba text → speech (`voice`: `female` or `male`); the `X-Voice-Model` header says which model spoke | `k2-fsa/OmniVoice` on ZeroGPU, cloning two Kamba speakers from Google FLEURS (CC-BY 4.0); falls back to `facebook/mms-tts-swh`, a Swahili voice on CPU |
| `GET /voice/prompts`, `POST /voice/recordings` | Speakers contribute Kikamba recordings for a future Kamba voice | — |
| `GET /stats`, `POST /feedback` | Usage counts and ratings | — |

Interactive docs: `/docs`.

## Configuration (Space settings)

| Variable | Value | Purpose |
|---|---|---|
| `NLLB_GPU_MODEL_ID` | `facebook/nllb-200-3.3B` | Translation model run on the GPU. Remove to translate on CPU only. |
| `TTS_GPU_MODEL_ID` | `k2-fsa/OmniVoice` | Voice model run on the GPU, cloning the speakers in `app/data/voices`. Remove to use only the Swahili voice. |
| `NLLB_MODEL_ID` | `facebook/nllb-200-distilled-1.3B` | CPU translation model (fallback when the GPU can't be used). |
| `VOICE_DATASET_REPO` | `lawmaluki/kamba-voice-recordings` | Private dataset that contributed recordings are pushed to every 5 minutes. |
| `HF_TOKEN` (secret) | a write token | Lets the Space push recordings to that dataset. |

API calls from the website carry no visitor token, so ZeroGPU charges them to one daily GPU
quota shared by the whole Space. When it runs out, translations continue on the CPU model.

Models load in the background after each start, so the first requests after a restart are
slow. Stats reset when the Space restarts. The models are licensed CC-BY-NC 4.0
(non-commercial use only).
