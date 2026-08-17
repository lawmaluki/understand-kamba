"""
Standalone test: translate a Kikamba string via app/translate.py, no ASR or
API layer involved. Loads .env manually since app/config.py doesn't.

Usage (from the kam-backend/ directory):
    python scripts/test_translate.py "Kikamba text here"
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app import translate  # noqa: E402


def main():
    if len(sys.argv) != 2:
        print('usage: python scripts/test_translate.py "Kikamba text"')
        sys.exit(1)

    text = sys.argv[1]
    print(f"Kikamba: {text}\n")

    sw = translate.translate(text, "Swahili")
    print(f"Swahili: {sw}\n")

    en = translate.translate(text, "English")
    print(f"English: {en}")


if __name__ == "__main__":
    main()
