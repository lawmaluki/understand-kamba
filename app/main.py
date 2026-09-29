"""
FastAPI wrapper: audio/video-link in, transcript + translations out.

Run with: uvicorn app.main:app --reload --env-file .env
Only after scripts/check_asr_model.py and scripts/test_transcribe.py have
both been run successfully -- see README.md.

Model inference is blocking, so every route that runs a model is either a
plain `def` (FastAPI runs those in a worker thread) or hands the work to
run_in_threadpool -- never call a model directly inside `async def`.
"""
import os
import uuid
from typing import Literal, Optional

from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import asr, audio, downloader, stats, tts
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
    # Keep only the extension (ffmpeg uses it as a format hint); the client's
    # filename never touches the path, so it can't escape temp_dir.
    src_path = _temp_path(os.path.splitext(os.path.basename(file.filename or ""))[1])
    limit = settings.upload_max_mb * 1024 * 1024

    try:
        size = 0
        with open(src_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, f"file exceeds {settings.upload_max_mb}MB limit")
                f.write(chunk)

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
            result = TranslateResponse(
                text=text,
                translation_kam=translate_mod.translate(text, KIKAMBA, source_language=ENGLISH),
            )
        elif req.direction == "kam_to_en":
            result = TranslateResponse(text=text, translation_en=translate_mod.translate(text, ENGLISH))
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


# Serves frontend/ at "/" -- registered last so it only catches requests that
# didn't match an API route above (e.g. GET /, /style.css, /app.js).
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
