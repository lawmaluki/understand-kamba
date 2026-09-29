# Understand Kamba — Project Documentation

English and Kikamba translation, Kikamba speech recognition, and read-aloud playback, running entirely on your own machine.

Last updated: 29 September 2026

## 1. Overview

Understand Kamba is a web app backed by a Python API. It lets you:

- translate English into Kikamba and Kikamba into English (and Kikamba into Swahili through the API),
- speak or upload Kikamba audio and get it transcribed to text,
- hear Kikamba text read aloud,
- rate, copy, share and save translations.

All models run locally. No paid API or account is needed with the default settings, and no text or audio leaves the machine running the backend.

**Status: working prototype.** Every feature in the interface is backed by a real model, but translation accuracy has not yet been checked by a Kikamba speaker, and the voice is a Swahili voice reading Kikamba (see section 9). Treat outputs as drafts, not authoritative translations.

## 2. Features at a glance

| Feature | How it works | Quality today |
|---|---|---|
| English to Kikamba, Kikamba to English | Meta NLLB-200 (distilled 600M) | Unverified by a Kikamba speaker. Kamba is low-resource in NLLB and some output shows Kikuyu-style grammar. |
| Kikamba speech to text | FarmerlineML/w2v-bert-2.0_kamba | About 30% word error rate and 7% character error rate on its publisher's own test set. |
| Read aloud | Meta MMS Swahili voice (facebook/mms-tts-swh) | Clear and intelligible, but with a Swahili accent; ĩ and ũ are read as i and u. |
| Usage stats and ratings | Counted by the backend, stored in data/ | Real numbers. |
| Copy, share, save | In the browser | Saved translations stay in that browser only. |
| Dialect selection | Label only | All four dialects use the same models, so the output does not change. |

## 3. How it fits together

The system has two parts that run side by side:

- **Backend** (app/): a FastAPI server on port 8000. It loads the models, serves the API, and keeps usage stats in data/.
- **Web app** (web/): a Next.js site on port 3000. It runs in the browser and calls the backend over HTTP.

What happens for each action:

| Action in the web app | Backend call | Model used |
|---|---|---|
| Translate | POST /translate | NLLB-200 |
| Speak or Upload (Kikamba mode) | POST /transcribe?translate=false, then POST /translate | w2v-BERT Kamba, then NLLB-200 |
| Play | POST /synthesize | MMS Swahili voice |
| Thumbs up or down | POST /feedback | none |
| Header stats | GET /stats | none |

Each model loads the first time it is needed, which takes 10 to 30 seconds. After that, requests take a few seconds on a typical CPU.

Audio uploads are converted to 16 kHz mono WAV with ffmpeg before transcription and are trimmed to the first 60 seconds. Temporary audio files are deleted as soon as each request finishes.

An older static interface in frontend/ is also served by the backend at http://localhost:8000/. It offers file upload, video-link transcription and Kikamba-to-Swahili/English text translation.

## 4. Getting started

### 4.1 Requirements

- Python 3.12 (3.10 or newer should work)
- Node.js 20 or newer, with npm
- About 8 GB of free disk space for the models, and 8 GB of RAM or more
- An internet connection the first time each model is used, to download it

A separate ffmpeg install is not needed: the backend uses ffmpeg from your PATH if there is one, and otherwise the copy bundled with the imageio-ffmpeg Python package.

### 4.2 Install

From the project folder:

```
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

cd web
npm install
```

### 4.3 Configure

Copy .env.example to .env in the project folder. The defaults work as they are; see section 6 for every setting.

To point the web app at a backend somewhere other than http://localhost:8000, copy web/.env.local.example to web/.env.local and set NEXT_PUBLIC_API_BASE_URL.

### 4.4 Run

Start the backend (from the project folder, with the virtual environment's Python):

```
venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000 --env-file .env
```

The --env-file flag matters: the app does not load .env by itself.

Start the web app in a second terminal:

```
cd web
npm run dev
```

Then open http://localhost:3000.

### 4.5 First run

The first translation, transcription and playback each download and load a model. Sizes: NLLB-200 about 4.7 GB, w2v-BERT Kamba about 2.3 GB, MMS Swahili voice about 140 MB. Models are cached in ~/.cache/huggingface/hub and are not downloaded again.

## 5. Using the web app

**Choose a direction.** The switch at the top right of the card selects English to Kikamba or Kikamba to English. Switching swaps the two sides, so your last translation carries over.

**Translate text.** Type in the left box and press Translate, or Ctrl+Enter (Cmd+Enter on a Mac). Input is limited to 500 characters. In English mode, the Sample button fills in an example sentence.

**Speak Kikamba.** In Kikamba to English mode, press Speak, talk, then press Stop (recording stops by itself after 60 seconds). Or press Upload and choose an audio or video file. The transcript appears in the left box and is translated automatically. The browser asks for microphone permission the first time; recording only works on localhost or over HTTPS.

**Listen.** In English to Kikamba mode, press the play button under the translation. The first press generates the audio and draws its waveform; later presses replay it.

**Rate.** Thumbs up or down rates the current translation once. Ratings update the "% rated helpful" figure in the header and are logged with the sentence for later review.

**Copy, share, save.** Copy puts the translation on the clipboard. Share opens your device's share menu, or copies both texts on a computer. Save adds the pair to the Saved translations list below the card; it is kept in this browser only and can be removed with the bin icon.

**Dialect.** The cards under Dialects & voices change the title and tag shown with the translation. The translation itself is the same for every dialect.

## 6. Configuration reference

Backend settings are read from environment variables, normally supplied through .env.

| Variable | Default | Purpose |
|---|---|---|
| TRANSLATION_BACKEND | nllb | nllb (local, free) or anthropic (Anthropic API, paid per request) |
| NLLB_MODEL_ID | facebook/nllb-200-distilled-600M | NLLB model to load. facebook/nllb-200-distilled-1.3B is larger and usually more accurate. |
| NLLB_NUM_BEAMS | 5 | Candidate translations compared per sentence. Higher is slightly better and slower. |
| ANTHROPIC_API_KEY | (empty) | Required only when TRANSLATION_BACKEND=anthropic |
| TRANSLATION_MODEL | (empty) | Claude model ID, required only when TRANSLATION_BACKEND=anthropic |
| MAX_TRANSLATE_CHARS | 500 | Longest text accepted. Keep in step with MAX_TRANSLATE_CHARS in web/src/lib/api.ts. |
| ASR_MODEL_ID | FarmerlineML/w2v-bert-2.0_kamba | Speech recognition model. facebook/mms-1b-all also works, but its Kamba support is unconfirmed. |
| ASR_TARGET_LANG | kam | Language adapter, used only with MMS models |
| MAX_AUDIO_SECONDS | 60 | Audio longer than this is trimmed. Keep in step with MAX_RECORDING_SECONDS in web/src/lib/api.ts. |
| SAMPLE_RATE | 16000 | Sample rate audio is converted to before transcription |
| TTS_MODEL_ID | facebook/mms-tts-swh | Voice model; any MMS/VITS text-to-speech model works |
| ALLOWED_ORIGINS | * | Sites allowed to call the API from a browser, comma-separated. Set to the web app's URL in production. |
| UPLOAD_MAX_MB | 25 | Largest audio upload accepted |
| TEMP_DIR | system temp folder/kam-backend | Where uploads are converted; files are deleted after each request |
| DATA_DIR | data/ in the project folder | Where stats.json and feedback.jsonl are kept |

Web app setting (web/.env.local):

| Variable | Default | Purpose |
|---|---|---|
| NEXT_PUBLIC_API_BASE_URL | http://localhost:8000 | Address of the backend |

## 7. Deploying

The two parts deploy to different places:

- **Web app** on Vercel (or any Next.js host). It is small and fits comfortably.
- **Backend** on a host that runs a long-lived server with about 8 GB of RAM and 10 GB of disk. It cannot run on Vercel: PyTorch and the other dependencies alone are about 5.5 GB, far over Vercel's 500 MB function limit, and the models need several GB of memory. Suitable hosts include a Hugging Face Space (Docker), Render, Railway, Fly.io or a VPS.

### 7.1 Backend

The repository's Dockerfile builds the backend image. It installs CPU-only PyTorch and listens on port 7860 (override with the PORT variable).

On a Hugging Face Space: create a Space with the Docker SDK, push this repository to it, and add the settings from section 6 as Space variables. The Space's README must start with a front-matter block containing sdk: docker and app_port: 7860.

On other hosts: point the host at the Dockerfile, expose port 7860, and set the environment variables there.

Set ALLOWED_ORIGINS to the web app's address, for example https://understand-kamba.vercel.app. The backend must be served over HTTPS, because browsers block an HTTPS page from calling an HTTP API.

Models download on the first request after each start unless the host keeps a persistent disk for HF_HOME, so the first request after a restart is slow. On hosts without a persistent disk, data/ (stats and ratings) is also reset on restart; set DATA_DIR to a persistent volume to keep it.

### 7.2 Web app on Vercel

1. In the Vercel project, open Settings, then Build and Deployment, and set **Root Directory** to web. Without this, Vercel finds requirements.txt at the top of the repository and tries to build the Python backend, which fails with "Total bundle size exceeds the maximum function size (500 MB)".
2. Under Settings, Environment Variables, add NEXT_PUBLIC_API_BASE_URL with the backend's HTTPS address.
3. Redeploy. The API address is built into the site at build time, so redeploy again whenever it changes.

## 8. API reference

All endpoints accept and return JSON unless noted. Errors return a JSON body of the form {"detail": "..."}. Interactive docs are available at http://localhost:8000/docs while the backend is running.

### POST /translate

Translates text.

Request:

```
{ "text": "Good morning, my friend.", "direction": "en_to_kam" }
```

direction is one of: en_to_kam, kam_to_en, or kam_to_sw_en (Kikamba to both Swahili and English; the default).

Response:

```
{ "text": "...", "translation_kam": "...", "translation_en": null, "translation_sw": null }
```

Only the fields for the requested direction are filled in.

Errors: 400 if the text is empty; 422 if it is longer than MAX_TRANSLATE_CHARS; 503 if the Anthropic backend is selected but not configured; 500 if the model fails.

### POST /transcribe

Transcribes Kikamba speech. Send the audio as multipart form data in a field named file. Any format ffmpeg reads works, including webm, m4a, mp3, wav and video files.

Query parameter translate (default true): when true, the transcript is also translated to Swahili and English.

Response:

```
{ "transcript": "...", "translation_sw": "...", "translation_en": "..." }
```

Errors: 413 if the file is larger than UPLOAD_MAX_MB; 500 if conversion or transcription fails.

### POST /transcribe-url

Same as /transcribe, but downloads the audio from a video or social-media link using yt-dlp (files up to 200 MB, 120-second download limit).

```
{ "url": "https://..." }
```

Errors: 400 if the link cannot be downloaded; 500 if transcription fails.

### POST /synthesize

Reads Kikamba text aloud. Returns audio/wav (16 kHz mono), not JSON.

```
{ "text": "Ũnĩ mũseo, mũnyanyawa." }
```

Errors: 422 if the text is empty or too long; 500 if generation fails.

### GET /stats

```
{ "translations": 42, "ratings_up": 10, "ratings_down": 3 }
```

translations counts successful /translate calls.

### POST /feedback

Records a rating and returns the updated stats.

```
{ "rating": "up", "direction": "en_to_kam", "text": "source text", "translation": "translated text" }
```

rating is up or down. Errors: 422 for any other value.

### GET /health

Returns {"status": "ok"}.

## 9. Models and quality

### Translation: NLLB-200

Meta's No Language Left Behind model includes Kamba (code kam_Latn), but Kamba had very little training data. The backend improves its output in three ways:

- each sentence is translated separately, because NLLB was trained on single sentences and drops sentences from longer paragraphs;
- five candidate translations are compared (beam search) instead of taking the first;
- output length is capped relative to the input, and repeated phrases are blocked, to stop runaway or invented text.

Known issue: some words appear to be wrong. For example, "Did you sleep well?" came out as "We nĩwasomie nesa?", where nĩwasomie may mean "did you read". A Kikamba speaker should review output before it is relied on.

### Speech recognition: w2v-BERT Kamba

A community fine-tune of Meta's w2v-BERT 2.0 published by Farmerline. Its model card reports a 30% word error rate and 7% character error rate, on a test set that is not described. In testing, words were mostly recognisable but sometimes merged or misspelled.

### Voice: MMS Swahili

No working Kikamba voice model exists publicly. The only one found (Musembi/speecht5-tts-kamba) has corrupted weights and outputs silence. The Swahili voice was chosen instead because Swahili spelling is close to Kikamba: when its Kikamba output was transcribed by the Kamba speech model, the text came back almost word for word. Limitations: Swahili accent and intonation, and the vowels ĩ and ũ are pronounced as plain i and u.

To switch voices later, set TTS_MODEL_ID to any MMS/VITS model, for example a future facebook/mms-tts-kam.

### Measuring accuracy

The most useful next step is a test set: 30 to 50 typical English sentences with Kikamba translations written by a speaker. Scoring each model against it gives a real accuracy figure and shows whether a larger model (NLLB 1.3B) or the Anthropic backend is worth using. The ratings log in data/feedback.jsonl is a good source of sentences that went wrong.

## 10. Data and privacy

| Data | Where it is kept | Lifetime |
|---|---|---|
| Uploaded and recorded audio | TEMP_DIR on the backend machine | Deleted when the request finishes |
| Translation count and rating totals | data/stats.json | Until deleted |
| Each rating with its source text and translation | data/feedback.jsonl | Until deleted |
| Saved translations | The browser's localStorage | Until removed in the app or browser data is cleared |
| Models | ~/.cache/huggingface/hub | Until deleted |

Text and audio are not sent to any outside service with the default settings. If TRANSLATION_BACKEND is set to anthropic, the text being translated is sent to the Anthropic API.

The data/ folder is excluded from git.

## 11. Project structure

```
understand-kamba/
  app/
    main.py         API endpoints
    config.py       settings from environment variables
    translate.py    translation (NLLB or Anthropic)
    asr.py          speech recognition
    tts.py          read-aloud voice
    audio.py        ffmpeg conversion
    downloader.py   audio from video links (yt-dlp)
    stats.py        translation count and ratings
  web/
    src/app/        page layout, global styles, colour tokens
    src/components/translator/
                    StudioCard (state and wiring), StudioHeader,
                    ContentArea, VoiceInput, AudioPlayer,
                    FooterControls, DialectSelector, SavedTranslations
    src/lib/        api.ts (backend calls), dialects.ts,
                    samples.ts, saved.ts (saved translations store)
  frontend/         older static interface served at localhost:8000
  scripts/          standalone model tests
  docs/             this documentation
  data/             stats and ratings (created on first use)
  .env.example      configuration template
  Dockerfile        backend image for deployment (section 7)
  requirements.txt  Python dependencies
```

The accent colour is butter yellow (#F8E27A), defined as the butter-50 to butter-900 scale in web/src/app/globals.css. Use butter-300 for fills and butter-700 or darker for text on white.

## 12. Troubleshooting

**"Couldn't reach the translation server" in the web app.** The backend is not running, or NEXT_PUBLIC_API_BASE_URL points somewhere else. Start the backend (section 4.4) and check http://localhost:8000/health.

**New endpoints return 404, or settings seem ignored.** An old backend process is still running. Stop whatever is using port 8000 and start it again with the command in section 4.4, including --env-file .env.

**The first request is very slow.** The model is downloading or loading; later requests are faster. Downloads need an internet connection.

**"Microphone access was blocked".** Allow the microphone for the site in the browser's address bar. Recording requires localhost or HTTPS.

**"No speech was recognised in that audio".** The recording was silent or too quiet, or not in Kikamba. Record closer to the microphone.

**Transcription fails with a file-not-found error.** ffmpeg could not be found. Reinstall dependencies with pip install -r requirements.txt so imageio-ffmpeg is present.

**Stats are not updating.** Stats are written to DATA_DIR by a single backend process. Running several backend workers at once is not supported.

## 13. Known limitations and next steps

- Translation accuracy is unmeasured. Build a speaker-checked test set (section 9).
- No real Kikamba voice. Revisit if Meta or the community publishes one.
- Dialect selection does not change the output; there are no per-dialect models.
- No formal-register option.
- No login, rate limiting or abuse protection. Add these, and set ALLOWED_ORIGINS, before deploying publicly.
- Stats storage supports a single backend process; move it to a database before scaling.
- No automated tests or deployment pipeline yet.
