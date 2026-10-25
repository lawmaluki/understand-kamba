"""
Select the most usable pairs from OPUS-NLLB English-Kikamba (1.63M machine-mined
pairs) for fine-tuning. Writes training/data/opus_filtered.tsv.gz.

Filters, in order:
  1. alignment score >= MIN_SCORE (the mining confidence shipped with the data)
  2. clean text: letters, no URLs/emoji/chat noise, 3-60 words, length ratio 0.5-2
  3. the Kikamba side looks like Kikamba (has Kikamba function words, few English ones)
  4. religious text removed (English and Kikamba keywords, Bible verse references)
  5. one pair per Kikamba sentence and per English sentence (best score wins)
  6. nothing that overlaps FLORES-200 dev or devtest (our evaluation data)
Then the top MAX_PAIRS by score are kept.

    python training/filter_opus.py
"""
import csv
import gzip
import io
import json
import os
import re
import unicodedata
import urllib.request
import zipfile

OPUS_URL = "https://object.pouta.csc.fi/OPUS-NLLB/v1/moses/en-kam.txt.zip"
MIN_SCORE = 1.06
MAX_PAIRS = 100_000

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "opus_filtered.tsv.gz")
CACHE = os.path.join(os.environ.get("TEMP", "/tmp"), "kamba-opus")

RELIGIOUS_EN = re.compile(
    r"\b(god|gods|jehovah|jesus|christ|christians?|bible|biblical|witness(es)?|kingdom|watchtower|lord|apostles?|"
    r"disciples?|scriptures?|pray(er|ers|ing|ed)?|church(es)?|satan|devil|angels?|paul|moses|abraham|david|israel(ites)?|"
    r"congregations?|faith|sins?|sinners?|holy|prophets?|prophecy|psalms?|gospel|heaven|worship(ers)?|spiritual|"
    r"elders|baptized|baptism|preach(ing|ed)?|ministry|resurrection|paradise|creator|jerusalem|bethel|pioneers?|missionar(y|ies)|circuit overseer)\b", re.I)
RELIGIOUS_KAM = re.compile(
    r"(ngai|yeova|yesũ|yesu|klĩsto|klisto|mbivilia|aklĩsto|aklisto|ũthaithi|uthaithi|mũsyaĩĩsya|ngũsĩ|maombi|"
    r"kĩkundi kya|atũmwa|mũtheu|muthaimi|nzama ya ngai|ũsumbĩ wa ngai|kanisa)", re.I)
VERSE = re.compile(r"\b\d{1,3}:\d{1,3}\b")
NOISE = re.compile(r"(https?://|www\.|@|#|\.com|\(trg\)|\(src\)|=|\|[\U0001F300-\U0001FAFF]|(\w)\2{3,})", re.I)
KAM_WORDS = {"na", "wa", "ya", "nĩ", "ni", "kana", "ũndũ", "undu", "ala", "ila", "kwa", "ta", "o", "mũno", "muno",
             "ũsu", "usu", "nũndũ", "nundu", "sya", "kya", "ma", "nĩkana", "vandũ", "andũ", "andu", "ũla", "ula"}
EN_WORDS = {"the", "and", "is", "are", "of", "to", "in", "that", "this", "with", "for", "you", "it", "was", "i", "my",
            "me", "just", "want", "wanna", "your", "be", "have", "not", "on", "at", "so", "love", "life"}
# Hindi/Urdu chat words that look like Kikamba ("kya", "na", "ke") and leaked into the mined data.
OTHER_WORDS = {"hai", "hain", "kyu", "kyun", "aap", "apka", "apke", "nahi", "nhi", "mein", "me", "ke", "ki", "ka", "ho",
               "kar", "raha", "tha", "bhi", "aur", "se", "ko", "yeh", "woh", "kuch", "naam", "baate", "ya", "pe"}


def clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text).strip()


def load_opus():
    os.makedirs(CACHE, exist_ok=True)
    names = {ext: os.path.join(CACHE, f"NLLB.en-kam.{ext}") for ext in ("en", "kam", "scores")}
    if not all(os.path.exists(p) for p in names.values()):
        print("downloading OPUS-NLLB en-kam (60 MB)...")
        with urllib.request.urlopen(OPUS_URL, timeout=300) as r:
            zipfile.ZipFile(io.BytesIO(r.read())).extractall(CACHE)
    read = lambda p: open(p, encoding="utf-8").read().split("\n")  # noqa: E731
    return read(names["en"]), read(names["kam"]), [float(x) for x in read(names["scores"]) if x]


def flores_sentences() -> set[str]:
    """FLORES-200 dev + devtest (training/data/flores200_*.tsv, from Meta's official release)."""
    out = set()
    for split in ("dev", "devtest"):
        with open(os.path.join(HERE, "data", f"flores200_{split}.tsv"), encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                out.add(clean(row["kam"]).lower())
                out.add(clean(row["eng"]).lower())
    return out


def keep(en: str, kam: str) -> str | None:
    """Return None to keep the pair, or the name of the filter that rejected it."""
    a, b = len(en.split()), len(kam.split())
    if not (3 <= a <= 60 and 3 <= b <= 60) or not (0.5 <= b / a <= 2.0):
        return "length"
    if NOISE.search(en) or NOISE.search(kam) or en.lower() == kam.lower():
        return "noise"
    if sum(c.isalpha() for c in kam) < 0.7 * len(kam.replace(" ", "")):
        return "noise"
    kw = [w.strip(".,;:!?\"'()").lower() for w in kam.split()]
    kam_hits = sum(w in KAM_WORDS for w in kw)
    has_tilde = any(c in kam for c in "ĩũĨŨ")
    # Mined Kikamba that is real is almost always written with ĩ/ũ; the junk (Hindi chat, other
    # Bantu languages, English lyrics) is not. Requiring them trades recall for precision.
    if not has_tilde or kam_hits == 0:
        return "not_kikamba"
    if any(w in EN_WORDS for w in kw) or any(w in OTHER_WORDS - {"ya", "na", "ka", "ke", "ki", "me"} for w in kw):
        return "not_kikamba"
    if RELIGIOUS_EN.search(en) or RELIGIOUS_KAM.search(kam) or VERSE.search(en) or VERSE.search(kam):
        return "religious"
    return None


def main():
    en_lines, kam_lines, scores = load_opus()
    flores = flores_sentences()
    reasons, seen_kam, seen_en, kept = {}, set(), set(), []
    for en, kam, score in zip(en_lines, kam_lines, scores):  # already sorted by score, best first
        if score < MIN_SCORE:
            reasons["score"] = reasons.get("score", 0) + 1
            continue
        en, kam = clean(en), clean(kam)
        why = keep(en, kam)
        if why is None and (kam.lower() in seen_kam or en.lower() in seen_en):
            why = "duplicate"
        if why is None and (kam.lower() in flores or en.lower() in flores):
            why = "flores_overlap"
        if why:
            reasons[why] = reasons.get(why, 0) + 1
            continue
        seen_kam.add(kam.lower())
        seen_en.add(en.lower())
        kept.append((kam, en, round(score, 4)))
        if len(kept) >= MAX_PAIRS:
            break

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["kam", "eng", "score"])
        w.writerows(kept)
    print(f"kept {len(kept):,} pairs -> {OUT}")
    print("rejected:", {k: f"{v:,}" for k, v in sorted(reasons.items(), key=lambda x: -x[1])})


if __name__ == "__main__":
    main()
