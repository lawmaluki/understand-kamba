"""
Build the clean Kikamba parallel training data in training/data/.

Only human-translated sources are kept. Everything else that is publicly
available was checked and left out on purpose (see training/README.md):
OPUS-NLLB (machine-mined, misaligned, mostly religious), FineTranslations
(English side is machine translation), Bloom (religious, CC-BY-NC-ND),
KnoxDevelopers (Bible verses).

Sources, downloaded from kithyadan/kikamba-corpus at a pinned commit:
  glotstorybook  children's stories, human translations (CC-BY-4.0 / CC-BY-NC-4.0)
  tatoeba        short conversational sentences (CC-BY-2.0-FR)
  flores200 dev  997 professional translations (CC-BY-SA-4.0). FLORES *devtest*
                 is our test set (eval/) and is never included here.

Any TSV files you add under training/data/community/ (columns: kam, eng or
kam, swh, with a header row) are merged in as well, so pairs translated by
Kamba speakers flow into the same files.

Output:
  training/data/kam_eng.tsv  columns kam, eng, source, license, doc
  training/data/kam_swh.tsv  columns kam, swh, source, license, doc
(doc = the story file a sentence comes from, so a test set can hold out whole stories)

    python training/build_parallel.py
"""
import csv
import glob
import json
import os
import re
import unicodedata
import urllib.request

COMMIT = "961744532eeacbfeba1fa67b4eaede3f47633485"
BASE = f"https://raw.githubusercontent.com/kithyadan/kikamba-corpus/{COMMIT}/data/parallel"
SOURCES = ["glotstorybook", "tatoeba", "flores200"]

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")
COMMUNITY = os.path.join(OUT, "community")


def clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text).strip()


def plausible(kam: str, other: str) -> bool:
    """Drop empty, truncated ('...') and badly misaligned pairs."""
    if not kam or not other or "..." in kam or "..." in other:
        return False
    a, b = len(kam.split()), len(other.split())
    return 0.4 <= a / b <= 2.5 if min(a, b) > 3 else True


def fetch(name: str) -> list[dict]:
    with urllib.request.urlopen(f"{BASE}/{name}.jsonl", timeout=60) as r:
        return [json.loads(line) for line in r.read().decode("utf-8").splitlines() if line.strip()]


def main():
    pairs = {"eng": {}, "swh": {}}  # lang -> {(kam, other): (source, license, doc)}
    dropped = 0
    for name in SOURCES:
        for rec in fetch(name):
            lang = rec.get("translation_lang")
            if lang not in pairs:
                continue
            if name == "flores200" and (rec.get("extra") or {}).get("flores_split") != "dev":
                continue  # devtest is the evaluation set
            kam, other = clean(rec["text"]), clean(rec["translation"])
            if not plausible(kam, other):
                dropped += 1
                continue
            doc = (rec.get("extra") or {}).get("file") or name  # the story a sentence belongs to
            pairs[lang].setdefault((kam, other), (name, rec["license"], doc))

    for path in sorted(glob.glob(os.path.join(COMMUNITY, "*.tsv"))):
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            lang = "eng" if "eng" in reader.fieldnames else "swh"
            if os.path.basename(path).startswith("test-"):
                continue  # held-out test pairs are never trained on
            for row in reader:
                kam, other = clean(row["kam"]), clean(row[lang])
                if kam and other:
                    src = f"community:{os.path.basename(path)}"
                    pairs[lang].setdefault((kam, other), (src, "project", src))

    os.makedirs(OUT, exist_ok=True)
    for lang, items in pairs.items():
        path = os.path.join(OUT, f"kam_{lang}.tsv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["kam", lang, "source", "license", "doc"])
            for (kam, other), (src, lic, doc) in items.items():
                w.writerow([kam, other, src, lic, doc])
        by_src = {}
        for src, _, _ in items.values():
            by_src[src] = by_src.get(src, 0) + 1
        print(f"kam_{lang}.tsv: {len(items)} pairs {by_src}")
    print(f"dropped {dropped} empty/truncated/misaligned pairs")


if __name__ == "__main__":
    main()
