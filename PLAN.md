# kam-backend — build plan

A minimal backend for a "chamgei-style" Kikamba speech-to-text + translation
service: audio/video/link in, transcript + Swahili/English translation out.
This is the plan we worked through in conversation, written down, plus one
important open question flagged below.

This backend is deliberately decoupled from KambaBench-ASR. KambaBench-ASR is
the long-term benchmark/model-quality effort (leakage control, native
validation, a properly fine-tuned model). This backend exists so there's a
working product loop *now*, using whatever baseline ASR is available, with
the model swapped out later once KambaBench-ASR produces something better.

---

## Open question to resolve first: does the MMS baseline actually support Kamba?

Your own `KambaBench-ASR/README.md` states "Kamba is supported by Meta's
Massively Multilingual Speech models." I tried to independently confirm this
against `facebook/mms-1b-all` (the all-language checkpoint) before writing
this scaffold, and could not get a clean confirmation — a fetch of that
model's `vocab.json` did not show a `kam` entry where alphabetically expected
(between `amk` and `ann`), and a fetch of its adapter file listing also
didn't surface one, though that listing was paginated and possibly
incomplete. I did **not** get a fully reliable answer either way — the tools
available to me here can't do a proper authenticated Hugging Face pull, and
page-scraping a huge JSON/file-tree through a summarizing fetch is exactly
the kind of check that produces false negatives.

**Don't take my word for it — `scripts/check_asr_model.py` in this scaffold
runs the real check** (loads the actual processor/adapter via `transformers`
with real network access) and tells you definitively. Run it first, before
building anything else on top of MMS.

If it turns out Kamba isn't in `mms-1b-all`:
- Check whether Meta's broader MMS release (1162 languages, per their
  research paper) has a Kamba checkpoint under a different repo/name —
  `mms-1b-all` is one specific checkpoint, not necessarily the full set.
  Search Hugging Face for other `facebook/mms-*` repos and their language
  lists.
- Search Hugging Face directly for any existing community Kamba ASR/Whisper
  fine-tune (I didn't find one in a first pass, but didn't do an exhaustive
  search).
- As a last resort, fall back to a general-purpose multilingual Whisper
  checkpoint (`whisper-large-v3`) with no Kamba fine-tuning — it will perform
  worse (Kamba isn't in its training data either), but it gives you an
  end-to-end pipeline to build and test the rest of the app against while
  KambaBench-ASR's own fine-tune is in progress.

---

## Pipeline

```
audio/video/link
      |
      v
[ingestion]  -- upload, or yt-dlp for URLs
      |
      v
[audio.py]   -- ffmpeg: convert to 16kHz mono WAV, trim to max duration
      |
      v
[asr.py]     -- MMS (or fallback model): audio -> Kikamba text
      |
      v
[translate.py] -- Kikamba text -> Swahili / English (LLM-based, see caveat)
      |
      v
   JSON response
```

## Translation caveat

NLLB-200 (the obvious off-the-shelf MT option) does not appear to include
Kamba in its 200 covered languages — again, not something I could verify with
full certainty from here, but the languages I could check around where
`kam`/`kam_Latn` should sit didn't show it. `translate.py` defaults to
LLM-based translation (prompting Claude directly) instead, since that's the
most available option for a language this low-resource, with the honest
caveat that quality will be inconsistent — Kikamba is low-resource in every
model's training data, not just NLLB's.

## Backend build order (matches what we discussed)

1. **`scripts/check_asr_model.py`** — confirm the ASR baseline actually works
   for Kamba before anything else. Don't skip this step.
2. **`app/asr.py`** — the transcription function on its own, tested via
   `scripts/test_transcribe.py` against a couple of real Kikamba clips before
   any API layer exists.
3. **`app/audio.py` + `app/downloader.py`** — file upload conversion and
   URL-to-audio extraction (yt-dlp). Build upload handling first since it's
   simpler; add the URL/social-link path second.
4. **`app/translate.py`** — Kikamba → Swahili/English via the Anthropic API.
5. **`app/main.py`** — FastAPI wrapper tying it together (`/transcribe`,
   `/transcribe-url`, `/health`). Synchronous for now; revisit as a job-queue
   pattern if video downloads make requests too slow.
6. **Hosting** — not set up in this scaffold. Options discussed: a small
   always-on GPU box (RunPod, Lambda), or a serverless GPU endpoint (Modal,
   Replicate, HF Inference Endpoints) that scales to zero when idle — the
   latter is the better fit while traffic is low and unpredictable.

## Things this scaffold deliberately does not handle yet

- Auth, rate limiting, abuse prevention.
- Async/job-queue handling for slow requests (long video downloads).
- Data retention policy — decide whether uploaded/recorded audio is stored
  or discarded. AfriVoices-KE's license carries explicit ethical-use
  restrictions (no surveillance, no exploitation); if this backend ever
  touches that corpus or a similarly-licensed one, that policy needs to be
  decided before shipping, not after.
- Tests.
- Deployment/CI.
