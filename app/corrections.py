"""
Translation corrections suggested by users: when a translation is wrong, the
web app lets people pick one of the model's alternative translations or type
their own. Each correction is a candidate training pair for the next
fine-tuning run (training/, after review by a Kikamba speaker).

Rows are appended to data/corrections/<session>/corrections.jsonl. When
settings.corrections_dataset_repo is set, a huggingface_hub CommitScheduler
pushes that folder to the (private) dataset every few minutes, so corrections
survive Space restarts. Each server process writes to its own session folder.

Nothing identifies the person: no name, account or IP address is stored (the
IP is held in memory for an hour only, by app/ratelimit.py).
"""
import json
import os
import secrets
import threading
import time
import uuid

from .config import settings

# Bump when the notice shown next to the correction box changes; stored with every row.
NOTICE_VERSION = "2026-10-14"
DIRECTIONS = {"en_to_kam", "kam_to_en"}
ORIGINS = {"suggestion", "edited", "typed"}  # picked as-is, picked then changed, written from scratch
DIALECTS = {"", "machakos", "kitui", "makueni", "elder", "other"}  # web/src/lib/dialects.ts

_SESSION = time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
_session_dir = os.path.join(settings.data_dir, "corrections", _SESSION)
_scheduler = None
_scheduler_lock = threading.Lock()
_write_lock = threading.Lock()


class RejectedCorrection(ValueError):
    """The correction failed validation; the message is shown to the user."""


def _get_scheduler():
    global _scheduler
    if not settings.corrections_dataset_repo:
        return None
    with _scheduler_lock:
        if _scheduler is None:
            from huggingface_hub import CommitScheduler

            os.makedirs(_session_dir, exist_ok=True)
            _scheduler = CommitScheduler(
                repo_id=settings.corrections_dataset_repo,
                repo_type="dataset",
                private=True,
                folder_path=_session_dir,
                path_in_repo=f"data/{_SESSION}",
                every=5,  # minutes
            )
        return _scheduler




def _norm(text: str) -> str:
    return " ".join(text.split())


def save_correction(*, direction: str, text: str, translation: str, correction: str,
                    origin: str, model: str = "", dialect: str = "") -> dict:
    """Validate and store one correction. Returns the stored row."""
    text, translation, correction = _norm(text), _norm(translation), _norm(correction)
    if direction not in DIRECTIONS or origin not in ORIGINS or dialect not in DIALECTS:
        raise RejectedCorrection("Invalid correction details.")
    if not text or not correction:
        raise RejectedCorrection("The correction is empty.")
    if correction.lower() == translation.lower():
        raise RejectedCorrection("That's the same as the original translation.")
    limit = settings.max_translate_chars
    if len(text) > limit or len(correction) > 2 * limit or len(translation) > 2 * limit:
        raise RejectedCorrection("The text is too long.")

    row = {
        "id": uuid.uuid4().hex,
        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "direction": direction,
        "source": text,
        "model_translation": translation,
        "correction": correction,
        "origin": origin,
        "model": model[:100],
        "dialect": dialect,
        "notice_version": NOTICE_VERSION,
        "reviewed": False,
    }
    scheduler = _get_scheduler()
    os.makedirs(_session_dir, exist_ok=True)
    # The scheduler's lock keeps a half-written line out of an upload.
    with (scheduler.lock if scheduler else _write_lock):
        with open(os.path.join(_session_dir, "corrections.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row
