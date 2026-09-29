"""
ffmpeg-based audio utilities. Uses ffmpeg from PATH if present, otherwise the
binary bundled with the imageio-ffmpeg package, so no system install is needed.
"""
import functools
import shutil
import subprocess


@functools.cache
def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def to_wav_16k_mono(src_path: str, dst_path: str, max_seconds: int | None = None) -> str:
    """Convert any ffmpeg-readable audio/video file to 16kHz mono WAV,
    optionally trimmed to max_seconds from the start."""
    cmd = [_ffmpeg(), "-y", "-i", src_path, "-ac", "1", "-ar", "16000"]
    if max_seconds:
        cmd += ["-t", str(max_seconds)]
    cmd += [dst_path]
    subprocess.run(cmd, check=True, capture_output=True)
    return dst_path
