# Understand Kamba

Open English ⇄ Kikamba translation, Kikamba speech recognition and a Kamba voice, running on free hosting.

- **Live app:** https://understand-kamba.vercel.app
- **API:** https://lawmaluki-understand-kamba-api.hf.space (interactive docs at `/docs`)

| Feature | Model | Where it runs |
|---|---|---|
| English ⇄ Kikamba, Kikamba → Swahili + English | Meta NLLB-200 3.3B (fallback: distilled 1.3B; local default: distilled 600M) | Hugging Face ZeroGPU |
| Kikamba speech → text | `FarmerlineML/w2v-bert-2.0_kamba` | CPU |
| Kikamba text → speech (Woman / Man) | `k2-fsa/OmniVoice` cloning two FLEURS Kamba speakers (fallback: MMS Swahili voice) | ZeroGPU |
| Voice contributions | `/contribute` page → private dataset | CPU |
| Stats, ratings, share card, saved translations | — | Backend / browser |

Measured quality, with confidence intervals, is in [docs/DOCUMENTATION.md §8](docs/DOCUMENTATION.md#8-models-and-quality) and the research paper ([paper/](paper/)).

## Documentation

| For | Read |
|---|---|
| People using the app | [docs/USER-GUIDE.md](docs/USER-GUIDE.md) |
| Developers: setup, configuration, API, structure | [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md) |
| Hosting on Hugging Face and why | [docs/BACKEND-HOSTING-MIGRATION.md](docs/BACKEND-HOSTING-MIGRATION.md) |
| Voice contributors, data handling, consent | [docs/CONTRIBUTOR-DATA-GUIDE.md](docs/CONTRIBUTOR-DATA-GUIDE.md) |
| Reproducing the evaluation | [eval/README.md](eval/README.md) |
| The research paper | [paper/understand_kamba.pdf](paper/understand_kamba.pdf) |

## Quick start (local)

Backend (Python 3.12):

```
python -m venv venv
venv\Scripts\activate            # Windows; macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # macOS/Linux: cp
uvicorn app.main:app --reload --reload-dir app --env-file .env
```

Web app (Node 20+), in another terminal:

```
cd web
npm install
npm run dev
```

Open http://localhost:3000. The web app calls `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`; see `web/.env.local.example`). Point it at the hosted API to skip running models locally.

Models download on first use (about 5 GB locally with the defaults). Locally the voice is the MMS Swahili fallback; OmniVoice and NLLB-3.3B run only on the Space's GPU.

## Project layout

```
app/        FastAPI backend: translate.py, asr.py, tts.py, voice.py, main.py, ...
  data/     reading prompts and the reference voices
web/        Next.js app (translator, share card, /contribute)
space/      Hugging Face Space entry point (ZeroGPU) and its requirements
scripts/    deploy_space.py, build_prompts.py, build_pdf.py, model checks
eval/       evaluation scripts, system outputs and score reports
paper/      research paper (LaTeX) and its generated numbers
docs/       documentation (Markdown + PDFs)
Dockerfile  CPU-only backend image for hosts other than the Space
```

## Licences

The deployed models are non-commercial: NLLB-200 (CC-BY-NC 4.0) and OmniVoice weights (CC-BY-NC). The reference voices are FLEURS recordings (CC-BY 4.0), credited in `app/data/voices/README.md`. The reading prompts are FLORES-200 sentences (CC-BY-SA 4.0).
