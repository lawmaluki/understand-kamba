"""
FastAPI wrapper: audio/video-link in, transcript + translations out.

Run with: uvicorn app.main:app --reload
Only after scripts/check_asr_model.py and scripts/test_transcribe.py have
both been run successfully -- see README.md.
"""
import os
import shutil
import uuid
from typing import Literal, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import asr, audio, downloader
from . import translate as translate_mod
from .config import settings

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


class TranslateRequest(BaseModel):
    text: str
    direction: Literal["kam_to_sw_en", "en_to_kam"] = "kam_to_sw_en"


class TranslateResponse(BaseModel):
    text: str
    translation_sw: Optional[str] = None
    translation_en: Optional[str] = None
    translation_kam: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok"}


def _process_audio_file(src_path: str) -> TranscribeResponse:
    os.makedirs(settings.temp_dir, exist_ok=True)
    wav_path = os.path.join(settings.temp_dir, f"{uuid.uuid4().hex}.wav")
    audio.to_wav_16k_mono(src_path, wav_path, max_seconds=settings.max_audio_seconds)

    try:
        transcript = asr.transcribe_wav_file(wav_path)
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)

    translation_sw = None
    translation_en = None
    if translate_mod.translation_available():
        translation_sw = translate_mod.translate(transcript, "Swahili")
        translation_en = translate_mod.translate(transcript, "English")

    return TranscribeResponse(
        transcript=transcript,
        translation_sw=translation_sw,
        translation_en=translation_en,
    )


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...)):
    os.makedirs(settings.temp_dir, exist_ok=True)
    src_path = os.path.join(settings.temp_dir, f"{uuid.uuid4().hex}_{file.filename}")

    size = 0
    with open(src_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.upload_max_mb * 1024 * 1024:
                f.close()
                os.remove(src_path)
                raise HTTPException(413, f"file exceeds {settings.upload_max_mb}MB limit")
            f.write(chunk)

    try:
        return _process_audio_file(src_path)
    except Exception as e:
        raise HTTPException(500, f"transcription failed: {e}")
    finally:
        if os.path.exists(src_path):
            os.remove(src_path)


@app.post("/transcribe-url", response_model=TranscribeResponse)
async def transcribe_url(req: TranscribeUrlRequest):
    try:
        src_path = downloader.download_audio_from_url(req.url)
    except Exception as e:
        raise HTTPException(400, f"could not fetch/extract audio from url: {e}")

    try:
        return _process_audio_file(src_path)
    except Exception as e:
        raise HTTPException(500, f"transcription failed: {e}")
    finally:
        if os.path.exists(src_path):
            os.remove(src_path)


@app.post("/translate", response_model=TranslateResponse)
async def translate_text(req: TranslateRequest):
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
            translation_kam = translate_mod.translate(
                text, "Kikamba (Kamba language, Kenya)", source_language="English"
            )
            return TranslateResponse(text=text, translation_kam=translation_kam)

        translation_sw = translate_mod.translate(text, "Swahili")
        translation_en = translate_mod.translate(text, "English")
    except Exception as e:
        raise HTTPException(500, f"translation failed: {e}")

    return TranslateResponse(
        text=text,
        translation_sw=translation_sw,
        translation_en=translation_en,
    )


# Serves frontend/ at "/" -- registered last so it only catches requests that
# didn't match an API route above (e.g. GET /, /style.css, /app.js).
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
