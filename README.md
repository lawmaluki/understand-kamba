# understandkamba

Turn speech into text, in Kikamba, Swahili, or English.

A FastAPI backend plus a Next.js web app (`web/`) for Kikamba:

| Feature | Model (all run locally) | Quality |
|---|---|---|
| English ⇄ Kikamba, Kikamba → Swahili translation | Meta NLLB-200 distilled 600M | Unverified by a Kikamba speaker; Kamba is low-resource in NLLB |
| Kikamba speech → text | `FarmerlineML/w2v-bert-2.0_kamba` | ~30% WER / 7% CER on its own (undocumented) eval set |
| Kikamba text → speech | Meta MMS **Swahili** voice (`facebook/mms-tts-swh`) | Intelligible, but Swahili accent; ĩ/ũ read as i/u. No working Kikamba voice exists — `Musembi/speecht5-tts-kamba` has NaN weights |
| Usage stats + 👍/👎 ratings | — | Real counts, stored in `data/` |

Full documentation: [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)
(PDF: `docs/Understand-Kamba-Documentation.pdf`).

**Deploying:** the web app goes on Vercel with Root Directory set to `web`;
the backend is too large for Vercel and runs from the `Dockerfile` on a host
with ~8 GB RAM. See section 7 of the documentation.

Models download on first use (~7 GB total). Dialect choices in the web UI
are labels only — every dialect uses the same models. `PLAN.md` has the
original build plan.

## Setup

1. Create a virtual environment and install dependencies:

   ```
   python -m venv venv
   venv\Scripts\activate        # Windows
   # source venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```

2. ffmpeg (audio conversion) needs no separate install: `app/audio.py` uses
   the one on PATH if present, otherwise the binary bundled with the
   `imageio-ffmpeg` package.

3. Copy `.env.example` to `.env`. The default translation backend (NLLB,
   run locally) needs no key; the first request downloads the model. To use
   the Anthropic backend instead, set `TRANSLATION_BACKEND=anthropic` plus
   `ANTHROPIC_API_KEY` and `TRANSLATION_MODEL`. The app doesn't load `.env`
   itself — pass `--env-file .env` to uvicorn (below); the `scripts/` load it
   with `python-dotenv`.

## Speech model

The default `ASR_MODEL_ID` is the Farmerline w2v-BERT Kamba fine-tune. Meta's
`facebook/mms-1b-all` also works (its `kam` adapter is loaded automatically),
but whether it really supports Kamba is unconfirmed — run
`python scripts/check_asr_model.py` before switching to it.

## Test transcription standalone

```
python scripts/test_transcribe.py path\to\a\kikamba\clip.wav
```

Any ffmpeg-readable format works, not just WAV.

## Run the API

```
uvicorn app.main:app --reload --env-file .env
```

Then, from another terminal:

```
curl -X POST http://localhost:8000/translate ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"Good morning, my friend.\", \"direction\": \"en_to_kam\"}"

curl -F "file=@clip.wav" http://localhost:8000/transcribe

curl -X POST http://localhost:8000/transcribe-url ^
  -H "Content-Type: application/json" ^
  -d "{\"url\": \"https://...\"}"

curl -X POST http://localhost:8000/synthesize ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"Ũnĩ mũseo\"}" --output speech.wav
```

(`^` is the Windows cmd line-continuation character; use `\` in bash.)

| Endpoint | Does |
|---|---|
| `POST /translate` | `direction`: `en_to_kam`, `kam_to_en`, or `kam_to_sw_en` (both) |
| `POST /transcribe` | Kikamba audio upload → transcript (+ translations unless `?translate=false`) |
| `POST /transcribe-url` | Same, from a video/social-media link |
| `POST /synthesize` | Kikamba text → WAV |
| `GET /stats`, `POST /feedback` | Translation count and 👍/👎 ratings; ratings are logged with their text to `data/feedback.jsonl` for review |

The first call to each model is slow (10–30 s) while it loads; later calls
take a few seconds.

## Web UI

```
cd web
npm install
npm run dev
```

Opens on http://localhost:3000 and calls the API at `NEXT_PUBLIC_API_BASE_URL`
(default `http://localhost:8000`; see `web/.env.local.example`). English ⇄
Kikamba switch, record or upload Kikamba speech, play translations aloud,
rate/share/save (saved translations live in the browser's localStorage).
Microphone recording needs `localhost` or HTTPS.

## What's not done yet

- No auth, rate limiting, or abuse prevention.
- No async/job-queue handling — a slow video download will block the request
  that triggered it.
- CORS is wide open (`allow_origins=["*"]`) — tighten before deploying
  anywhere public.
- Translation quality is unverified and expected to be inconsistent — see
  `app/translate.py`'s docstring.
- No real Kikamba voice, and no per-dialect or formal-register models.
- Stats/feedback use JSON files with a process-local lock — single worker only.
- No data-retention policy decided (are uploaded/recorded clips stored or
  discarded?) — see `PLAN.md`.
- No tests, no deployment/CI, not hosted anywhere yet.

## Project layout

```
understand-kamba/
├── PLAN.md                    # full build plan + the open ASR-support question
├── README.md                  # this file
├── requirements.txt
├── .env.example
├── app/
│   ├── config.py               # settings from environment variables
│   ├── asr.py                  # CTC speech model (w2v-BERT Kamba or MMS): audio -> Kikamba text
│   ├── audio.py                # ffmpeg conversion/trim helpers
│   ├── downloader.py           # yt-dlp: video/social URL -> audio file
│   ├── translate.py            # Kikamba <-> Swahili/English/... (NLLB local, or Anthropic)
│   ├── tts.py                  # Kikamba text -> speech (MMS Swahili voice)
│   ├── stats.py                # translation count + ratings, stored in data/
│   └── main.py                 # FastAPI app (endpoints above)
├── data/                       # stats.json + feedback.jsonl (gitignored, created on first use)
├── frontend/                   # older static UI served by main.py at "/" -- upload, URL, text tabs
├── web/                        # Next.js translator UI (see "Web UI")
│   └── src/
└── scripts/
    ├── check_asr_model.py      # checks MMS has a Kamba adapter (only if using MMS)
    ├── test_transcribe.py      # transcribe one file, no API involved
    └── test_translate.py       # standalone translation test, no API layer involved
```
