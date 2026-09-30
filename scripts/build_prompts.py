"""
Build app/data/kikamba_prompts.tsv -- the Kikamba sentences shown on the
"record your voice" page -- from FLORES-200.

FLORES-200 Kamba sentences are professional translations in standard
orthography, licensed CC-BY-SA 4.0 (credit kept in the file header).
Download https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz,
extract it, then:

    python scripts/build_prompts.py path/to/flores200_dataset
"""
import os
import re
import sys

OUT = os.path.join(os.path.dirname(__file__), "..", "app", "data", "kikamba_prompts.tsv")


def main(flores_dir: str):
    prompts = []
    for split in ("dev", "devtest"):
        path = os.path.join(flores_dir, split, f"kam_Latn.{split}")
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f.read().splitlines(), 1):
                text = " ".join(line.split())
                # Comfortable to read aloud: 40-140 characters, and no digits
                # (read inconsistently), quotes or brackets.
                if 40 <= len(text) <= 140 and not re.search(r'[0-9()\[\]"“”]', text):
                    prompts.append((f"flores-{split}-{i}", text))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Kikamba sentences to read aloud on the voice-recording page.\n")
        f.write("# Source: FLORES-200 (kam_Latn dev + devtest), Meta Platforms, CC-BY-SA 4.0,\n")
        f.write("# https://github.com/facebookresearch/flores. Built by scripts/build_prompts.py.\n")
        f.write("id\ttext\n")
        for pid, text in prompts:
            f.write(f"{pid}\t{text}\n")
    print(f"{len(prompts)} prompts -> {OUT}")
    for _, text in prompts[:5]:
        print("  ", text)


if __name__ == "__main__":
    main(sys.argv[1])
