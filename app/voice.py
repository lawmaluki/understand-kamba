"""
Voice-recording contributions: native Kikamba speakers read sentences aloud
in the web app, building the dataset a real Kamba voice model needs.

Recordings are converted to 16 kHz mono WAV and stored in the Hugging Face
"audiofolder" layout (audio files + metadata.jsonl) under
data/voice/<session>/. When settings.voice_dataset_repo is set, a
huggingface_hub CommitScheduler pushes that folder to the (private) dataset
repo every few minutes. Each server process writes to its own session folder,
so a restarted Space never overwrites what an earlier one uploaded.
"""
import csv
import functools
import json
import os
import secrets
import threading
import time
import uuid
from collections import defaultdict, deque

import numpy as np
import soundfile as sf

from . import audio
from .config import settings

# Bump when the consent wording in the web app changes; stored with every recording.
CONSENT_VERSION = "2026-09-30"
DIALECTS = {"machakos", "kitui", "makueni", "other"}
GENDERS = {"", "female", "male", "other"}
AGE_RANGES = {"", "18-29", "30-44", "45-59", "60+"}
PROMPTS_FILE = os.path.join(os.path.dirname(__file__), "data", "kikamba_prompts.tsv")

_SESSION = time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
_session_dir = os.path.join(settings.data_dir, "voice", _SESSION)
_scheduler = None
_scheduler_lock = threading.Lock()
_write_lock = threading.Lock()
_recent: dict[str, deque] = defaultdict(deque)  # client IP -> upload times, for rate limiting


class RejectedRecording(ValueError):
    """The recording or its details failed validation; the message is shown to the user."""


@functools.cache
def prompts() -> dict[str, str]:
    """id -> Kikamba sentence to read aloud."""
    with open(PROMPTS_FILE, encoding="utf-8") as f:
        rows = csv.DictReader((line for line in f if not line.startswith("#")), delimiter="\t")
        return {row["id"]: row["text"] for row in rows}


def _get_scheduler():
    global _scheduler
    if not settings.voice_dataset_repo:
        return None
    with _scheduler_lock:
        if _scheduler is None:
            from huggingface_hub import CommitScheduler

            os.makedirs(_session_dir, exist_ok=True)
            _scheduler = CommitScheduler(
                repo_id=settings.voice_dataset_repo,
                repo_type="dataset",
                private=True,
                folder_path=_session_dir,
                path_in_repo=f"data/{_SESSION}",
                every=5,  # minutes
            )
        return _scheduler


def check_rate_limit(client_ip: str) -> None:
    now = time.time()
    times = _recent[client_ip]
    while times and now - times[0] > 3600:
        times.popleft()
    if len(times) >= settings.voice_uploads_per_hour:
        raise RejectedRecording("Too many recordings from this connection in the last hour. Please try again later.")
    times.append(now)


def save_recording(
    src_path: str,
    *,
    prompt_id: str,
    speaker_id: str,
    dialect: str,
    gender: str,
    age_range: str,
    consent: bool,
) -> dict:
    """Validate, convert and store one recording. Returns its metadata row."""
    if not consent:
        raise RejectedRecording("Consent is required to contribute a recording.")
    text = prompts().get(prompt_id)
    if text is None:
        raise RejectedRecording("Unknown sentence.")
    try:
        speaker_id = str(uuid.UUID(speaker_id))
    except ValueError:
        raise RejectedRecording("Invalid contributor ID.")
    if dialect not in DIALECTS or gender not in GENDERS or age_range not in AGE_RANGES:
        raise RejectedRecording("Invalid speaker details.")

    rel_path = f"audio/{speaker_id}/{uuid.uuid4().hex}.wav"
    dst_path = os.path.join(_session_dir, *rel_path.split("/"))
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    # Trim to the limit + 1 s so an over-long recording is detected, not silently cut.
    audio.to_wav_16k_mono(src_path, dst_path, max_seconds=settings.voice_max_seconds + 1)

    samples, sample_rate = sf.read(dst_path, dtype="float32")
    duration = len(samples) / sample_rate
    problem = None
    if duration < 1:
        problem = "The recording is too short."
    elif duration > settings.voice_max_seconds:
        problem = f"Recordings must be under {settings.voice_max_seconds} seconds."
    elif float(np.sqrt(np.mean(samples**2))) < 0.003:
        problem = "The recording is silent. Check your microphone and try again."
    if problem:
        os.remove(dst_path)
        raise RejectedRecording(problem)

    row = {
        "file_name": rel_path,
        "text": text,
        "prompt_id": prompt_id,
        "speaker_id": speaker_id,
        "dialect": dialect,
        "gender": gender,
        "age_range": age_range,
        "duration_seconds": round(duration, 2),
        "sample_rate": sample_rate,
        "consent_version": CONSENT_VERSION,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    scheduler = _get_scheduler()
    # The scheduler's lock keeps a half-written metadata line out of an upload.
    with (scheduler.lock if scheduler else _write_lock):
        with open(os.path.join(_session_dir, "metadata.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row
