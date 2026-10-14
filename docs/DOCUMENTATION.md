# Understand Kamba — Project Documentation

English and Kikamba translation, Kikamba speech recognition, and a Kamba voice. Live at https://understand-kamba.vercel.app, with the API on a free Hugging Face ZeroGPU Space; everything also runs on your own machine.

Last updated: 9 October 2026

This is the developer documentation. App users: see USER-GUIDE.md. Voice contributors and data handling: see CONTRIBUTOR-DATA-GUIDE.md. Evaluation: eval/README.md and the paper in paper/.

## 1. Overview

Understand Kamba is a web app backed by a Python API. It lets you:

- translate English into Kikamba and Kikamba into English (and Kikamba into Swahili through the API),
- speak or upload Kikamba audio and get it transcribed to text,
- hear Kikamba text read aloud,
- rate, copy, share and save translations.

All models are open and run on the backend itself, locally or on the Hugging Face Space. No paid API is needed with the default settings, and no text or audio is sent to a third-party service.

**Status: deployed, evaluated, not human-verified.** Every feature is backed by a real model and each component has been measured on public test sets (section 8), but no Kikamba speaker has systematically rated the output. Treat translations as drafts, not authoritative.

## 2. Features at a glance

| Feature | How it works | Quality today |
|---|---|---|
| English to Kikamba, Kikamba to English | Hosted: NLLB-200 1.3B fine-tuned for Kikamba (lawmaluki/nllb-200-1.3B-kamba-ft), on the GPU with the same model as CPU fallback. Locally: NLLB-200 distilled 600M | Fine-tuned model: FLORES chrF++ 44 Kikamba → English, 33 English → Kikamba; everyday sentences 37 and 29 (section 8). Not yet rated by Kikamba speakers. |
| Kikamba speech to text | FarmerlineML/w2v-bert-2.0_kamba | 11% character / 33% word error rate on FLEURS test, ignoring ĩ/ũ. |
| Read aloud | Hosted: OmniVoice (k2-fsa) on the Space's GPU, cloning a Kamba woman or man from Google FLEURS. Local, and fallback: Meta MMS Swahili voice | OmniVoice: Kamba pronunciation including ĩ and ũ; the Kamba speech model mishears about 7% of characters. Swahili fallback: Swahili accent, ĩ and ũ read as i and u (14%). |
| Usage stats and ratings | Counted by the backend, stored in data/ | Real numbers. |
| Copy, share, save | In the browser | Share creates an image card (Post 4:5 or Story 9:16) drawn in the browser. Saved translations stay in that browser only. |
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
| Play | POST /synthesize | OmniVoice Kamba voice (hosted), else MMS Swahili voice |
| Thumbs up or down | POST /feedback | none |
| Header stats | GET /stats | none |

Each model loads the first time it is needed, which takes 10 to 30 seconds. After that, requests take a few seconds on a typical CPU.

Audio uploads are converted to 16 kHz mono WAV with ffmpeg before transcription and are trimmed to the first 60 seconds. Temporary audio files are deleted as soon as each request finishes.

The backend serves no page of its own: opening http://localhost:8000/ redirects to the interactive API docs. (An older static interface, frontend/, was removed in October 2026; its video-link transcription is still available through POST /transcribe-url but not yet in the web app.)

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

**Copy, share, save.** Copy puts the translation on the clipboard. Save adds the pair to the Saved translations list below the card; it is kept in this browser only and can be removed with the bin icon.

**Share as an image.** Share opens "Share this translation" with a preview of a card for social media: the Understand Kamba name, the direction, the original text, the translation in large type, a waveform and the site address, on a pale cream background. Choose **Post 4:5** (1080×1350, for Instagram, Facebook, X and WhatsApp) or **Story 9:16** (1080×1920, for Stories, Status and TikTok). Long text shrinks to fit, and very long text is cut off with "…". Then:

- **Share** sends the image to your phone's share sheet (WhatsApp, Instagram and so on), or Windows' share menu.
- **Copy image** puts the PNG on the clipboard, for pasting into a post on a computer.
- **Download** saves it as understand-kamba-translation.png.
- **Copy text** copies the original, the translation and the site address.

Share and Copy image only appear in browsers that support them. The card is drawn entirely in the browser (web/src/lib/shareCard.ts), so it uses no server or GPU time.

**Dialect.** The cards under Dialects & voices change the title and tag shown with the translation. The translation itself is the same for every dialect.

**Record your voice (/contribute).** Kikamba speakers can help build a real Kamba voice. The page is linked from the home page ("Record your voice") and from the note under the play button. Contributors read a short explanation of how recordings are used, choose their dialect (gender and age are optional), confirm they are 18+ and fluent, and agree. They then see one Kikamba sentence at a time: record (up to 20 seconds), listen back, then submit, re-record or skip. The browser remembers the anonymous contributor ID and progress; "Ask to delete my recordings" opens a GitHub issue with that ID.

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
| ASR_MODEL_ID | FarmerlineML/w2v-bert-2.0_kamba | Speech recognition model. facebook/mms-1b-all (with ASR_TARGET_LANG=kam) is more accurate on FLEURS (7% vs 11% character error, section 8) but larger and slower; test it on real app recordings before switching. |
| ASR_TARGET_LANG | kam | Language adapter, used only with MMS models |
| MAX_AUDIO_SECONDS | 60 | Audio longer than this is trimmed. Keep in step with MAX_RECORDING_SECONDS in web/src/lib/api.ts. |
| SAMPLE_RATE | 16000 | Sample rate audio is converted to before transcription |
| TTS_MODEL_ID | facebook/mms-tts-swh | Voice model; any MMS/VITS text-to-speech model works |
| UPLOAD_MAX_MB | 25 | Largest audio upload accepted |
| TEMP_DIR | system temp folder/kam-backend | Where uploads are converted; files are deleted after each request |
| DATA_DIR | data/ in the project folder | Where usage stats and ratings (data/stats/), corrections (data/corrections/) and voice recordings (data/voice/) are kept |
| VOICE_DATASET_REPO | (empty) | Hugging Face dataset that contributed recordings are pushed to every 5 minutes, e.g. lawmaluki/kamba-voice-recordings. Empty keeps recordings local only. Needs HF_TOKEN with write access. |
| VOICE_MAX_SECONDS | 20 | Longest recording accepted |
| VOICE_UPLOAD_MAX_MB | 5 | Largest recording upload accepted |
| VOICE_UPLOADS_PER_HOUR | 120 | Recordings accepted per connection per hour |
| CORRECTIONS_DATASET_REPO | <voice dataset owner>/kamba-translation-corrections | Private Hugging Face dataset that translation corrections are pushed to every 5 minutes. Empty (no VOICE_DATASET_REPO either) keeps them local under data/corrections. |
| CORRECTIONS_PER_HOUR | 60 | Corrections accepted per connection per hour |
| NLLB_GPU_MODEL_ID | (empty) | Hugging Face Space only (space/server.py): translation model run on the ZeroGPU GPU, e.g. lawmaluki/nllb-200-1.3B-kamba-ft. NLLB_MODEL_ID becomes the CPU fallback. |
| STATS_DATASET_REPO | <voice dataset owner>/kamba-app-stats | Private dataset the usage counts and ratings are synced to every 5 minutes, so they survive restarts. Empty keeps them local only. |
| TTS_GPU_MODEL_ID | (empty) | Hugging Face Space only: voice model run on the ZeroGPU GPU, k2-fsa/OmniVoice, cloning the speakers in app/data/voices. TTS_MODEL_ID becomes the fallback. |

Web app setting (web/.env.local):

| Variable | Default | Purpose |
|---|---|---|
| NEXT_PUBLIC_API_BASE_URL | http://localhost:8000 | Address of the backend |

## 7. API reference

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
{ "text": "...", "translation_kam": "...", "translation_en": null, "translation_sw": null,
  "model": "lawmaluki/nllb-200-1.3B-kamba-ft" }
```

Only the fields for the requested direction are filled in. model names the model that produced the translation; on the Hugging Face Space it shows whether the GPU model or the CPU fallback answered.

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

Reads Kikamba text aloud. Returns audio/wav (mono; 24 kHz from OmniVoice, 16 kHz from the Swahili fallback), not JSON.

```
{ "text": "Ũnĩ mũseo, mũnyanyawa.", "voice": "female" }
```

voice is female (default) or male. It selects the OmniVoice speaker; the Swahili fallback has only one voice. The X-Voice-Model response header names the model that spoke (k2-fsa/OmniVoice or facebook/mms-tts-swh) and is readable by the website.

Errors: 422 if the text is empty or too long, or voice is anything else; 500 if generation fails.

### GET /stats

```
{ "translations": 42, "ratings_up": 10, "ratings_down": 3 }
```

translations counts successful /translate calls.

### POST /translate/suggestions

Other likely translations of a text (the runners-up of the beam search), offered as starting points when a user corrects a translation. Runs on the Space's GPU when available.

```
{ "text": "Ilinda yii ni yaasa.", "direction": "kam_to_en", "translation": "This line is long." }
→ { "suggestions": ["...", "...", "..."], "model": "lawmaluki/nllb-200-1.3B-kamba-ft" }
```

`translation` (the current one) is left out of the suggestions. Empty with the Anthropic backend.

### POST /corrections

Saves a user's correction (see app/corrections.py and CONTRIBUTOR-DATA-GUIDE.md).

```
{ "direction": "kam_to_en", "text": "source", "translation": "model output", "correction": "the right translation",
  "origin": "suggestion | edited | typed", "dialect": "machakos" }
```

Errors: 422 if the correction is empty or the same as the translation, 429 after CORRECTIONS_PER_HOUR submissions from one connection.

### POST /feedback

Records a rating and returns the updated stats.

```
{ "rating": "up", "direction": "en_to_kam", "text": "source text", "translation": "translated text" }
```

rating is up or down. Errors: 422 for any other value.

### GET /voice/prompts

The Kikamba sentences contributors read aloud (1,044 from FLORES-200), plus the current consent version and recording limit.

```
{ "prompts": [{ "id": "flores-dev-12", "text": "..." }], "consent_version": "2026-09-30", "max_seconds": 20 }
```

### POST /voice/recordings

Stores one contributed recording. Multipart form data:

| Field | Required | Notes |
|---|---|---|
| file | yes | The recording (any format ffmpeg reads, such as the browser's webm) |
| prompt_id | yes | The id of the sentence read, from /voice/prompts |
| speaker_id | yes | The contributor's anonymous UUID |
| dialect | yes | machakos, kitui, makueni or other |
| consent | yes | Must be true |
| gender | no | female, male, other, or empty |
| age_range | no | 18-29, 30-44, 45-59, 60+, or empty |

The recording is converted to 16 kHz mono WAV and stored with a metadata row (the sentence text is taken from the server's list, not the client). Response: {"ok": true, "duration_seconds": 5.7}.

Errors: 413 if the upload is over VOICE_UPLOAD_MAX_MB; 422 with a readable message if consent is missing, the details are invalid, or the recording is under 1 second, over VOICE_MAX_SECONDS or silent; 429 past VOICE_UPLOADS_PER_HOUR.

### GET /health

Returns {"status": "ok"}.

## 8. Models and quality

### Translation: NLLB-200

Meta's No Language Left Behind model includes Kamba (code kam_Latn), but Kamba had very little training data. The backend improves its output in three ways:

- each sentence is translated separately, because NLLB was trained on single sentences and drops sentences from longer paragraphs;
- five candidate translations are compared (beam search) instead of taking the first;
- output length is capped relative to the input, and repeated phrases are blocked, to stop runaway or invented text.

Known issue: some words appear to be wrong. For example, "Did you sleep well?" came out as "We nĩwasomie nesa?", where nĩwasomie may mean "did you read". A Kikamba speaker should review output before it is relied on.

Measured on the full FLORES-200 devtest (1,012 sentences; chrF++, higher is better; 95% confidence intervals in eval/results/mt_flores_devtest.json):

| Model | Kikamba → English | English → Kikamba (raw) | English → Kikamba (ĩ/ũ folded) |
|---|---|---|---|
| distilled 600M | 32.4 | 27.6 | 35.2 |
| distilled 1.3B | 34.5 | **28.0** | **35.7** |
| 3.3B | **34.9** | 24.0 | 29.8 |

- Kikamba → English improves with size, but 1.3B and 3.3B are statistically tied (p = 0.07).
- English → Kikamba: the 3.3B model is significantly *worse* than both smaller models. It writes longer output and adds content that is not in the source. The 1.3B model is the best choice for this direction.
- Only 35% of the FLORES Kikamba reference sentences use ĩ and ũ, while the models always do, so raw English → Kikamba scores partly measure spelling. The folded column treats ĩ/i and ũ/u as the same.

**Fine-tuned model (live since 14 October 2026).** Since 1.3B was the best base model, it was fine-tuned with LoRA on about 10,200 existing public sentence pairs: human-translated children's stories, FLORES dev, and a filtered 0.5% of the OPUS web pairs (see training/README.md). Compared with the base 1.3B model on sentences it never saw (chrF++; details in eval/results/finetune_nllb_1.3B.json):

| Test set | Direction | Base 1.3B | Fine-tuned | Change |
|---|---|---|---|---|
| 91 sentences from 10 held-out children's stories (everyday) | Kikamba → English | 25.5 | **37.1** | +11.6 |
| | English → Kikamba | 26.8 | **29.2** | +2.5 |
| FLORES devtest (1,012 sentences) | Kikamba → English | 34.1 | **44.3** | +10.2 |
| | English → Kikamba | 27.7 | **33.4** | +5.7 |

(These were scored line by line, without the app's sentence splitting, so the base numbers differ slightly from the table above.) Only 2 test sentences in each set have a near-copy in the training data. The hosted backend runs this model (lawmaluki/nllb-200-1.3B-kamba-ft) on the Space's GPU and also as its CPU fallback; the local default remains the 600M model. The model and its description are public on Hugging Face.

It still gets key words wrong ("Ilinda yii ni yaasa", *this dress is long*, comes out as "this line is long"). Users can now correct translations in the app (section 9); reviewed corrections are used to retrain it.

Known issue: the sentence splitter also splits after initials and titles ("John F. Kennedy", "Dr."), which affects about 2% of sentences.

### Speech recognition: w2v-BERT Kamba

A community fine-tune of Meta's w2v-BERT 2.0 published by Farmerline. On the FLEURS Kamba test set (827 recordings) it gets 10.8% of characters and 33% of words wrong when ĩ/ũ are ignored (14.3% and 43% counting them, since it rarely writes the tildes). Women and men are recognised equally well within the margin of error. Meta's facebook/mms-1b-all with its Kamba adapter does better on the same test (7.2% of characters, 30% of words, ignoring ĩ/ũ), but it was trained on FLEURS training audio, so part of that advantage may not carry over to everyday speech. Details: eval/results/asr_fleurs_test.json.

### Voice: OmniVoice cloning Kamba speakers

The hosted backend reads Kikamba with OmniVoice (k2-fsa, 2026; model weights CC-BY-NC, code Apache-2.0), a 0.6-billion-parameter text-to-speech model covering 600+ languages. Its training data included 14.7 hours of Kamba, most likely from Google's FLEURS dataset. Its own default voice does not work for Kamba (no recognisable speech on two of five test sentences), so it clones one of two 8-second recordings of real Kamba speakers, a woman and a man, from FLEURS (app/data/voices, CC-BY 4.0). Visitors choose Woman or Man next to the play button.

Measured on 100 FLEURS test sentences, the Kamba speech model misheard 6.8% (woman) and 7.0% (man) of characters from the cloned voices, against 14.1% for the Swahili voice, 25.1% for the Kikuyu voice and 10.7% for the real FLEURS recordings. Beating real speech does not mean the voice is more natural: synthetic speech is clean, and OmniVoice was very likely trained on FLEURS audio, possibly including these sentences. Details: eval/results/tts_asr_roundtrip.json. It runs on the Space's ZeroGPU GPU (about 7 to 9 seconds per request including queueing), in full precision: casting it to float16 made it output silence. When the GPU can't be used, the Swahili voice below reads the text and the player says so.

The FLEURS speakers recorded for research. Before wider public use, consider replacing the reference clips with recordings from Kamba speakers who agree to be the app's voice; see app/data/voices/README.md.

### Fallback voice: MMS Swahili

Before OmniVoice, no working Kikamba voice model was found publicly. The only one found (Musembi/speecht5-tts-kamba) has corrupted weights and outputs silence. The Swahili voice was chosen instead because Swahili spelling is close to Kikamba: when its Kikamba output was transcribed by the Kamba speech model, the text came back almost word for word. Limitations: Swahili accent and intonation, and the vowels ĩ and ũ are pronounced as plain i and u.

To switch voices later, set TTS_MODEL_ID to any MMS/VITS model, for example a future facebook/mms-tts-kam. Meta's Kikuyu (mms-tts-kik) and Tharaka (mms-tts-thk) voices, both related languages, were also tried; the Kamba speech model misheard 17% and 22% of characters from them, against 8% for Swahili. The /contribute page collects the recordings needed to train a genuine Kamba voice.

### Measuring accuracy

All numbers above come from eval/ (see eval/README.md for how to reproduce them) and are discussed in the research paper in paper/. FLORES and FLEURS are Wikipedia-style read text and do not reflect everyday conversation, and no Kikamba speaker has rated the output yet, so the most useful next steps are a small native-speaker rating study and a second test set of everyday sentences with speaker-written Kikamba translations. The ratings log (data/stats/feedback/) and the users' corrections are good sources of sentences that went wrong.

## 9. Data and privacy

| Data | Where it is kept | Lifetime |
|---|---|---|
| Uploaded and recorded audio | TEMP_DIR on the backend machine | Deleted when the request finishes |
| Translation count and rating totals | data/stats/stats.json; on the hosted backend also the private dataset lawmaluki/kamba-app-stats | Until deleted |
| Each rating with its source text and translation | data/stats/feedback/; on the hosted backend also lawmaluki/kamba-app-stats | Until deleted |
| Translation corrections (source, model translation, correction, dialect) | data/corrections/; on the hosted backend the private dataset lawmaluki/kamba-translation-corrections | Until deleted; approved pairs are published in training/data/community/ |
| Saved translations | The browser's localStorage | Until removed in the app or browser data is cleared |
| Contributed voice recordings and their metadata (sentence, anonymous ID, dialect, optional gender and age range) | data/voice/ locally; on the hosted backend, the private dataset lawmaluki/kamba-voice-recordings | Until deleted, for example on the contributor's request |
| Contributor ID, details and progress | The contributor's browser (localStorage) | Until browser data is cleared |
| Models | ~/.cache/huggingface/hub | Until deleted |

Text and audio are not sent to any outside service with the default settings. If TRANSLATION_BACKEND is set to anthropic, the text being translated is sent to the Anthropic API.

The data/ folder is excluded from git.

## 10. Project structure

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
    voice.py        contributed voice recordings
    data/           kikamba_prompts.tsv (sentences to read aloud),
                    voices/ (Kamba reference clips for OmniVoice)
  web/
    src/app/        home page, /contribute page, global styles, colour tokens
    src/components/translator/
                    StudioCard (state and wiring), StudioHeader,
                    ContentArea, VoiceInput, AudioPlayer,
                    FooterControls, ShareCardDialog, DialectSelector,
                    SavedTranslations
    src/components/contribute/
                    ContributeCta (home-page invitation), ContributeStudio,
                    ConsentStep, RecordingStep
    src/lib/        api.ts (backend calls), dialects.ts, samples.ts,
                    saved.ts, contributor.ts (browser stores),
                    useRecorder.ts (microphone recording),
                    shareCard.ts (draws the share image)
  space/            Hugging Face Space entry point and config
  scripts/          model tests, deploy_space.py, build_prompts.py,
                    build_pdf.py
  eval/             evaluation scripts, outputs and score reports (eval/README.md)
  paper/            research paper (LaTeX), make_numbers.py
  docs/             this documentation, USER-GUIDE.md, CONTRIBUTOR-DATA-GUIDE.md
  data/             stats and ratings (created on first use)
  Dockerfile        backend image for hosts other than the Space (CPU only)
  .env.example      configuration template
  requirements.txt  Python dependencies
```

The accent colour is butter yellow (#F8E27A), defined as the butter-50 to butter-900 scale in web/src/app/globals.css. Use butter-300 for fills and butter-700 or darker for text on white.

## 11. Troubleshooting

**"Couldn't reach the translation server" in the web app.** The backend is not running, or NEXT_PUBLIC_API_BASE_URL points somewhere else. Start the backend (section 4.4) and check http://localhost:8000/health.

**New endpoints return 404, or settings seem ignored.** An old backend process is still running. Stop whatever is using port 8000 and start it again with the command in section 4.4, including --env-file .env.

**The first request is very slow.** The model is downloading or loading; later requests are faster. Downloads need an internet connection.

**"Microphone access was blocked".** Allow the microphone for the site in the browser's address bar. Recording requires localhost or HTTPS.

**"No speech was recognised in that audio".** The recording was silent or too quiet, or not in Kikamba. Record closer to the microphone.

**Transcription fails with a file-not-found error.** ffmpeg could not be found. Reinstall dependencies with pip install -r requirements.txt so imageio-ffmpeg is present.

**Stats are not updating.** Stats are written to DATA_DIR by a single backend process. Running several backend workers at once is not supported.

## 12. Known limitations and next steps

- Accuracy is measured automatically (section 8) but not yet by Kikamba speakers.
- Translation quality depends on everyday Kikamba data; grow it by reviewing user corrections and retraining (CONTRIBUTOR-DATA-GUIDE.md, section 7).
- The voices clone FLEURS speakers who did not consent to being the app's voice; replace them with consenting speakers (CONTRIBUTOR-DATA-GUIDE.md, section 7).
- Dialect selection does not change the output; there are no per-dialect models.
- No formal-register option.
- No login, rate limiting or abuse protection, and CORS allows any origin. Tighten these before deploying publicly.
- Stats storage supports a single backend process (synced to a dataset every 5 minutes); move it to a database before scaling.
- No automated tests or deployment pipeline yet.
