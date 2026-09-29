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

| Endpoint | Does |
|---|---|
| `POST /translate` | English ⇄ Kikamba (Meta NLLB-200) |
| `POST /transcribe` | Kikamba speech → text (FarmerlineML/w2v-bert-2.0_kamba) |
| `POST /synthesize` | Kikamba text → speech (Meta MMS Swahili voice) |
| `GET /stats`, `POST /feedback` | Usage counts and ratings |

Interactive docs: `/docs`. Models run on CPU and load in the background after each start,
so the first requests after a restart are slow. Stats reset when the Space restarts.

The models are licensed CC-BY-NC 4.0 (non-commercial use only).
