"""
Stage-1 standalone test: transcribe one local audio file from the command
line, with no API layer involved. Run this after check_asr_model.py succeeds,
and before trying app/main.py, so you're testing one thing at a time.

Usage (from the kam-backend/ directory):
    python scripts/test_transcribe.py path/to/clip.wav
    python scripts/test_transcribe.py path/to/clip.mp3   # any ffmpeg-readable format
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import asr, audio  # noqa: E402


def main():
    if len(sys.argv) != 2:
        print("usage: python scripts/test_transcribe.py <audio_file>")
        sys.exit(1)

    src = sys.argv[1]
    if not os.path.exists(src):
        print(f"file not found: {src}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp:
        wav_path = os.path.join(tmp, "clip.wav")
        print("Converting to 16kHz mono WAV...")
        audio.to_wav_16k_mono(src, wav_path)

        print("Transcribing (first run downloads model weights, can take a while)...")
        text = asr.transcribe_wav_file(wav_path)

        print("\n--- Transcript ---")
        print(text)
        print("------------------")


if __name__ == "__main__":
    main()
