"""
Build the clean Kikamba parallel training data in training/data/.

Only human-translated sources are kept. Everything else that is publicly
available was checked and left out on purpose (see training/README.md):
OPUS-NLLB (machine-mined, misaligned, mostly religious), FineTranslations
(English side is machine translation), Bloom (religious, CC-BY-NC-ND),
KnoxDevelopers (Bible verses).

Sources (frozen in training/data/kam_eng.tsv and kam_swh.tsv; originally from kithyadan/kikamba-corpus,
commit 9617445, which has since been rewritten without them):
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


def main():
    pairs = {"eng": {}, "swh": {}}  # lang -> {(kam, other): (source, license, doc)}
    dropped = 0
    # Public pairs: frozen in the repo. They came from kithyadan/kikamba-corpus (commit 9617445,
    # September 2026), which has since been rewritten without these files.
    for lang in pairs:
        path = os.path.join(OUT, f"kam_{lang}.tsv")
        with open(path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                if not row["source"].startswith("community:"):
                    pairs[lang].setdefault((row["kam"], row[lang]), (row["source"], row["license"], row["doc"]))

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
