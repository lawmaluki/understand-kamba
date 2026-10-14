"""
Real usage numbers for the UI: how many translations have been served, and
how users rated them. Counts live in data/stats/stats.json; every rating is
also appended to data/stats/feedback/<session>.jsonl with its text, so bad
translations can be reviewed.

The free Hugging Face Space has no permanent disk, so when
settings.stats_dataset_repo is set the data/stats folder is pushed to that
private dataset every few minutes (huggingface_hub CommitScheduler), and a
restarted server continues from the counts saved there instead of zero.

Single-process only -- a threading lock guards the files.
"""
import json
import os
import secrets
import shutil
import threading
import time

from .config import settings

_lock = threading.Lock()
_EMPTY = {"translations": 0, "ratings_up": 0, "ratings_down": 0}
_DIR = os.path.join(settings.data_dir, "stats")
_SESSION = time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
_scheduler = None
_ready = False


def _path(*parts: str) -> str:
    return os.path.join(_DIR, *parts)


def _restore() -> None:
    """Once per process: put stats.json in place, from the dataset if the server restarted."""
    global _ready
    if _ready:
        return
    _ready = True
    os.makedirs(_path("feedback"), exist_ok=True)
    if os.path.exists(_path("stats.json")):
        return
    legacy = os.path.join(settings.data_dir, "stats.json")  # location before stats were synced
    if os.path.exists(legacy):
        shutil.copy(legacy, _path("stats.json"))
        return
    if settings.stats_dataset_repo:
        try:
            from huggingface_hub import hf_hub_download

            saved = hf_hub_download(settings.stats_dataset_repo, "stats.json", repo_type="dataset")
            shutil.copy(saved, _path("stats.json"))
        except Exception as e:  # first run (no dataset yet) or Hub unreachable: start from zero
            print(f"[stats] no saved stats restored ({type(e).__name__})", flush=True)


def _get_scheduler():
    global _scheduler
    if _scheduler is None and settings.stats_dataset_repo:
        from huggingface_hub import CommitScheduler

        _scheduler = CommitScheduler(
            repo_id=settings.stats_dataset_repo,
            repo_type="dataset",
            private=True,
            folder_path=_DIR,
            every=5,  # minutes
        )
    return _scheduler


def _read() -> dict:
    try:
        with open(_path("stats.json"), encoding="utf-8") as f:
            return {**_EMPTY, **json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_EMPTY)


def _write(stats: dict) -> None:
    tmp = _path("stats.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(stats, f)
    os.replace(tmp, _path("stats.json"))  # atomic, so a crash can't truncate it


class _Guard:
    """Holds the module lock and, when syncing, the scheduler's lock, so an
    upload never sees a half-written file."""

    def __enter__(self):
        _lock.acquire()
        _restore()
        try:
            self._scheduler = _get_scheduler()
        except Exception as e:  # never let syncing break the app
            print(f"[stats] dataset sync unavailable ({e})", flush=True)
            self._scheduler = None
        if self._scheduler:
            self._scheduler.lock.acquire()
        return self

    def __exit__(self, *exc):
        if self._scheduler:
            self._scheduler.lock.release()
        _lock.release()


def get() -> dict:
    with _lock:
        _restore()
        return _read()


def record_translation() -> None:
    with _Guard():
        stats = _read()
        stats["translations"] += 1
        _write(stats)


def record_feedback(rating: str, direction: str, text: str, translation: str) -> dict:
    """rating is "up" or "down". Returns the updated stats."""
    with _Guard():
        entry = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "rating": rating,
            "direction": direction,
            "text": text,
            "translation": translation,
        }
        with open(_path("feedback", f"{_SESSION}.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        stats = _read()
        stats["ratings_up" if rating == "up" else "ratings_down"] += 1
        _write(stats)
        return stats
