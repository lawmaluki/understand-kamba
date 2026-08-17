"""
Extracts audio from a video/social-media URL via yt-dlp. This is the fiddliest
of the three input modes (chamgei's record/upload/link) -- different
platforms break in different ways. Build and test upload handling first;
treat this as a second pass.
"""
import os
import subprocess
import sys
import uuid

from .config import settings


def download_audio_from_url(url: str, timeout_seconds: int = 120) -> str:
    """Download and extract the best audio track from url, save as WAV.
    Returns the path to the downloaded file. Raises on failure (bad URL,
    unsupported platform, network error, timeout, etc.) -- catch this at the
    API layer and return a clean 400, don't let it bubble up raw."""
    os.makedirs(settings.temp_dir, exist_ok=True)
    out_id = uuid.uuid4().hex
    out_template = os.path.join(settings.temp_dir, f"{out_id}.%(ext)s")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-x", "--audio-format", "wav",
        "--max-filesize", "200M",
        "--no-playlist",
        "-o", out_template,
        url,
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=timeout_seconds)

    expected = os.path.join(settings.temp_dir, f"{out_id}.wav")
    if os.path.exists(expected):
        return expected

    # yt-dlp sometimes keeps a different extension despite -x/--audio-format;
    # fall back to scanning for the id.
    for fname in os.listdir(settings.temp_dir):
        if fname.startswith(out_id):
            return os.path.join(settings.temp_dir, fname)

    raise RuntimeError("yt-dlp did not produce an output file")
