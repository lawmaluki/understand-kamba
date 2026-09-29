"""
Real usage numbers for the UI: how many translations have been served, and
how users rated them. Counts live in data/stats.json; every rating is also
appended to data/feedback.jsonl with its text, so bad translations can be
reviewed (and later used as correction data).

Single-process only -- a threading lock guards the files. Swap for a real
database before running several workers.
"""
import json
import os
import threading
import time

from .config import settings

_lock = threading.Lock()
_EMPTY = {"translations": 0, "ratings_up": 0, "ratings_down": 0}


def _path(name: str) -> str:
    return os.path.join(settings.data_dir, name)


def _read() -> dict:
    try:
        with open(_path("stats.json"), encoding="utf-8") as f:
            return {**_EMPTY, **json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_EMPTY)


def _write(stats: dict) -> None:
    os.makedirs(settings.data_dir, exist_ok=True)
    tmp = _path("stats.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(stats, f)
    os.replace(tmp, _path("stats.json"))  # atomic, so a crash can't truncate it


def get() -> dict:
    with _lock:
        return _read()


def record_translation() -> None:
    with _lock:
        stats = _read()
        stats["translations"] += 1
        _write(stats)


def record_feedback(rating: str, direction: str, text: str, translation: str) -> dict:
    """rating is "up" or "down". Returns the updated stats."""
    with _lock:
        os.makedirs(settings.data_dir, exist_ok=True)
        entry = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "rating": rating,
            "direction": direction,
            "text": text,
            "translation": translation,
        }
        with open(_path("feedback.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        stats = _read()
        stats["ratings_up" if rating == "up" else "ratings_down"] += 1
        _write(stats)
        return stats
