"""
Per-visitor limits on the expensive routes, so one visitor or bot can't use up
the Space's shared daily GPU quota (or tie up the CPU) for everyone else.

A sliding one-hour window per (bucket, client IP), kept in memory: a restart
resets it, and several server processes would each keep their own counts.
Limits are set in app/config.py (*_PER_HOUR); a limit of 0 disables a bucket.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

WINDOW = 3600  # seconds

_lock = threading.Lock()
_hits: dict[tuple[str, str], deque] = defaultdict(deque)
_last_sweep = time.time()


def client_ip(request: Request) -> str:
    # Behind the Hugging Face proxy the client is the first X-Forwarded-For entry.
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def allow(bucket: str, ip: str, limit: int) -> bool:
    """Record one request; False if the visitor already made `limit` in the last hour."""
    global _last_sweep
    if limit <= 0:
        return True
    now = time.time()
    with _lock:
        if now - _last_sweep > WINDOW:  # forget visitors who have gone quiet
            for key in [k for k, q in _hits.items() if not q or now - q[-1] > WINDOW]:
                del _hits[key]
            _last_sweep = now
        times = _hits[(bucket, ip)]
        while times and now - times[0] > WINDOW:
            times.popleft()
        if len(times) >= limit:
            return False
        times.append(now)
        return True


def check(request: Request, bucket: str, limit: int, what: str) -> None:
    """Raise HTTP 429 with a readable message when the visitor is over the limit."""
    if not allow(bucket, client_ip(request), limit):
        raise HTTPException(
            429,
            f"You've made a lot of {what} requests in the last hour. Please wait a few minutes and try again.",
        )
