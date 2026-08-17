# kam-backend

Minimal FastAPI backend for a "chamgei-style" Kikamba speech-to-text +
translation service: audio recording, file upload, or a video/social-media
link goes in; a transcript and Swahili/English translation come out.

This is a scaffold, not a finished product. Read `PLAN.md` first — it
documents the build order and one important open question (whether the
default ASR baseline actually supports Kamba) that needs resolving before the
rest of this is worth trusting.

## Setup

1. Create a virtual environment and install dependencies:

   ```
   python -m venv venv
   venv\Scripts\activate        # Windows
   # source venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```

2. Install ffmpeg if you don't already have it (required for audio
   conversion — `app/audio.py` shells out to `ffmpeg`/`ffprobe`):
   - Windows: https://ffmpeg.org/download.html (add the `bin` folder to PATH)
   - macOS: `brew install ffmpeg`
   - Linux: `apt install ffmpeg` (or your distro's equivalent)

3. Copy `.env.example` to `.env` and fill in `ANTHROPIC_API_KEY` and
   `TRANSLATION_MODEL` (check https://docs.claude.com for the current model
   identifier). Load it however you prefer — e.g. `pip install python-dotenv`
   and add `from dotenv import load_dotenv; load_dotenv()` at the top of
   `app/main.py`, or just `set`/`export` the variables in your shell.

## Step 1 — verify the ASR model actually supports Kamba

**Do this before anything else.** See `PLAN.md` for why this isn't a given.

```
python scripts/check_asr_model.py
```

If it fails, see `PLAN.md`, "Fallback if MMS has no Kamba adapter" — don't
proceed to steps 2/3 until you have a model that passes this check (or you've
deliberately swapped in a fallback and updated `ASR_MODEL_ID` accordingly).

## Step 2 — test transcription standalone

```
python scripts/test_transcribe.py path\to\a\kikamba\clip.wav
```

Any ffmpeg-readable format works, not just WAV.

## Step 3 — run the API

```
uvicorn app.main:app --reload
```

Then, from another terminal:

```
curl -F "file=@clip.wav" http://localhost:8000/transcribe

curl -X POST http://localhost:8000/transcribe-url ^
  -H "Content-Type: application/json" ^
  -d "{\"url\": \"https://...\"}"
```

(`^` is the Windows cmd line-continuation character; use `\` in bash/PowerShell.)

## What's not done yet

- No auth, rate limiting, or abuse prevention.
- No async/job-queue handling — a slow video download will block the request
  that triggered it.
- CORS is wide open (`allow_origins=["*"]`) — tighten before deploying
  anywhere public.
- Translation quality is unverified and expected to be inconsistent — see
  `app/translate.py`'s docstring.
- No data-retention policy decided (are uploaded/recorded clips stored or
  discarded?) — see `PLAN.md`.
- No tests, no deployment/CI, not hosted anywhere yet.

## Project layout

```
kam-backend/
├── PLAN.md                    # full build plan + the open ASR-support question
├── README.md                  # this file
├── requirements.txt
├── .env.example
├── app/
│   ├── config.py               # settings from environment variables
│   ├── asr.py                  # MMS wrapper: audio -> Kikamba text
│   ├── audio.py                # ffmpeg conversion/trim helpers
│   ├── downloader.py           # yt-dlp: video/social URL -> audio file
│   ├── translate.py            # Kikamba -> Swahili/English (LLM-based)
│   └── main.py                 # FastAPI app: /transcribe, /transcribe-url, /health
└── scripts/
    ├── check_asr_model.py      # run first: does the Kamba adapter exist?
    └── test_transcribe.py      # run second: transcribe one file, no API involved
```
