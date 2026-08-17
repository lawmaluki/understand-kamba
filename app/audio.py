"""
ffmpeg-based audio utilities. Requires ffmpeg + ffprobe on PATH.
"""
import json
import subprocess


def get_duration_seconds(path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json", path,
        ],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def to_wav_16k_mono(src_path: str, dst_path: str, max_seconds: int | None = None) -> str:
    """Convert any ffmpeg-readable audio/video file to 16kHz mono WAV,
    optionally trimmed to max_seconds from the start."""
    cmd = ["ffmpeg", "-y", "-i", src_path, "-ac", "1", "-ar", "16000"]
    if max_seconds:
        cmd += ["-t", str(max_seconds)]
    cmd += [dst_path]
    subprocess.run(cmd, check=True, capture_output=True)
    return dst_path
