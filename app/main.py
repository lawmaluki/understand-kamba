"""
FastAPI wrapper: audio/video-link in, transcript + translations out.

Run with: uvicorn app.main:app --reload --env-file .env
Only after scripts/check_asr_model.py and scripts/test_transcribe.py have
both been run successfully -- see README.md.

Model inference is blocking, so every route that runs a model is either a
plain `def` (FastAPI runs those in a worker thread) or hands the work to
run_in_threadpool -- never call a model directly inside `async def`.
"""
import functools
import os
import uuid
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import asr, audio, downloader, stats, tts, voice
from . import translate as translate_mod
from .config import settings
from .translate import ENGLISH, KIKAMBA, SWAHILI

app = FastAPI(title="kam-backend", version="0.1.0")

# Wide open for local dev. Tighten allow_origins before deploying anywhere
# public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranscribeUrlRequest(BaseModel):
    url: str


class TranscribeResponse(BaseModel):
    transcript: str
    translation_sw: Optional[str] = None
    translation_en: Optional[str] = None


Direction = Literal["kam_to_sw_en", "kam_to_en", "en_to_kam"]


class TranslateRequest(BaseModel):
    text: str = Field(max_length=settings.max_translate_chars)
    direction: Direction = "kam_to_sw_en"


class TranslateResponse(BaseModel):
    text: str
    translation_sw: Optional[str] = None
    translation_en: Optional[str] = None
    translation_kam: Optional[str] = None
    model: Optional[str] = None  # which model produced it (e.g. GPU model vs CPU fallback)


class SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=settings.max_translate_chars)


class FeedbackRequest(BaseModel):
    rating: Literal["up", "down"]
    direction: Direction
    text: str = Field(max_length=settings.max_translate_chars)
    translation: str = Field(max_length=settings.max_translate_chars * 4)


class StatsResponse(BaseModel):
    translations: int
    ratings_up: int
    ratings_down: int


def _remove_quietly(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _temp_path(suffix: str = "") -> str:
    os.makedirs(settings.temp_dir, exist_ok=True)
    return os.path.join(settings.temp_dir, uuid.uuid4().hex + suffix)


async def _save_upload(file: UploadFile, limit_mb: int) -> str:
    """Stream an upload to a temp file (caller deletes it). Raises 413 past limit_mb."""
    # Keep only the extension (ffmpeg uses it as a format hint); the client's
    # filename never touches the path, so it can't escape temp_dir.
    path = _temp_path(os.path.splitext(os.path.basename(file.filename or ""))[1])
    size = 0
    try:
        with open(path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > limit_mb * 1024 * 1024:
                    raise HTTPException(413, f"file exceeds {limit_mb}MB limit")
                f.write(chunk)
    except BaseException:
        _remove_quietly(path)
        raise
    return path


@app.get("/health")
def health():
    return {"status": "ok"}


def _process_audio_file(src_path: str, translate: bool = True) -> TranscribeResponse:
    wav_path = _temp_path(".wav")
    try:
        audio.to_wav_16k_mono(src_path, wav_path, max_seconds=settings.max_audio_seconds)
        transcript = asr.transcribe_wav_file(wav_path)
    finally:
        _remove_quietly(wav_path)

    if not translate or not transcript or not translate_mod.translation_available():
        return TranscribeResponse(transcript=transcript)
    return TranscribeResponse(
        transcript=transcript,
        translation_sw=translate_mod.translate(transcript, SWAHILI),
        translation_en=translate_mod.translate(transcript, ENGLISH),
    )


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...), translate: bool = True):
    """Kikamba audio -> transcript. Pass ?translate=false to skip the
    Swahili/English translations (the web UI translates separately)."""
    src_path = await _save_upload(file, settings.upload_max_mb)
    try:
        return await run_in_threadpool(_process_audio_file, src_path, translate)
    except Exception as e:
        raise HTTPException(500, f"transcription failed: {e}")
    finally:
        _remove_quietly(src_path)


@app.post("/transcribe-url", response_model=TranscribeResponse)
def transcribe_url(req: TranscribeUrlRequest):
    try:
        src_path = downloader.download_audio_from_url(req.url)
    except Exception as e:
        raise HTTPException(400, f"could not fetch/extract audio from url: {e}")

    try:
        return _process_audio_file(src_path)
    except Exception as e:
        raise HTTPException(500, f"transcription failed: {e}")
    finally:
        _remove_quietly(src_path)


@app.post("/translate", response_model=TranslateResponse)
def translate_text(req: TranslateRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "text must not be empty")
    if not translate_mod.translation_available():
        raise HTTPException(
            503,
            "translation not configured -- set ANTHROPIC_API_KEY and "
            "TRANSLATION_MODEL in .env (or switch TRANSLATION_BACKEND to nllb)",
        )

    try:
        if req.direction == "en_to_kam":
            kam, model = translate_mod.translate_with_model(text, KIKAMBA, source_language=ENGLISH)
            result = TranslateResponse(text=text, translation_kam=kam, model=model)
        elif req.direction == "kam_to_en":
            en, model = translate_mod.translate_with_model(text, ENGLISH)
            result = TranslateResponse(text=text, translation_en=en, model=model)
        else:
            result = TranslateResponse(
                text=text,
                translation_sw=translate_mod.translate(text, SWAHILI),
                translation_en=translate_mod.translate(text, ENGLISH),
            )
    except Exception as e:
        raise HTTPException(500, f"translation failed: {e}")

    stats.record_translation()
    return result


@app.post("/synthesize", response_class=Response)
def synthesize(req: SynthesizeRequest):
    """Kikamba text -> 16 kHz WAV. Experimental voice; see app/tts.py."""
    try:
        wav = tts.synthesize_wav(req.text)
    except Exception as e:
        raise HTTPException(500, f"speech synthesis failed: {e}")
    return Response(content=wav, media_type="audio/wav")


@app.get("/stats", response_model=StatsResponse)
def get_stats():
    return stats.get()


@app.post("/feedback", response_model=StatsResponse)
def feedback(req: FeedbackRequest):
    return stats.record_feedback(req.rating, req.direction, req.text, req.translation)


class VoicePrompt(BaseModel):
    id: str
    text: str


class VoicePromptsResponse(BaseModel):
    prompts: list[VoicePrompt]
    consent_version: str
    max_seconds: int


@app.get("/voice/prompts", response_model=VoicePromptsResponse)
def voice_prompts():
    """Kikamba sentences for contributors to read aloud (see app/voice.py)."""
    return VoicePromptsResponse(
        prompts=[VoicePrompt(id=k, text=v) for k, v in voice.prompts().items()],
        consent_version=voice.CONSENT_VERSION,
        max_seconds=settings.voice_max_seconds,
    )


@app.post("/voice/recordings")
async def voice_recording(
    request: Request,
    file: UploadFile = File(...),
    prompt_id: str = Form(...),
    speaker_id: str = Form(...),
    dialect: str = Form(...),
    consent: bool = Form(...),
    gender: str = Form(""),
    age_range: str = Form(""),
):
    """Store one contributed recording of a prompt sentence."""
    # Behind the Hugging Face proxy the client is the first X-Forwarded-For entry.
    forwarded = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    try:
        voice.check_rate_limit(client_ip)
    except voice.RejectedRecording as e:
        raise HTTPException(429, str(e))

    src_path = await _save_upload(file, settings.voice_upload_max_mb)
    try:
        row = await run_in_threadpool(
            functools.partial(
                voice.save_recording, src_path, prompt_id=prompt_id, speaker_id=speaker_id,
                dialect=dialect, gender=gender, age_range=age_range, consent=consent,
            )
        )
    except voice.RejectedRecording as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"could not save recording: {e}")
    finally:
        _remove_quietly(src_path)
    return {"ok": True, "duration_seconds": row["duration_seconds"]}


# Serves frontend/ at "/" -- registered last so it only catches requests that
# didn't match an API route above (e.g. GET /, /style.css, /app.js).
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
