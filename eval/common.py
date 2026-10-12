"""
Shared evaluation protocol for the Understand Kamba paper.

Everything that affects a reported number is pinned here: the bootstrap
settings, the text normalizer, the edit-distance routine and the shape of the
"protocol" block written next to every result. Every system is scored by the
same code path against the same references.
"""
import hashlib
import json
import os
import platform
import re
import sys
import time
import unicodedata

import numpy as np

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(EVAL_DIR)
DATA_DIR = os.path.join(EVAL_DIR, "data")  # downloaded test sets (not committed)
OUTPUT_DIR = os.path.join(EVAL_DIR, "outputs")  # system outputs (committed: small text)
RESULTS_DIR = os.path.join(EVAL_DIR, "results")  # score reports (committed)

BOOTSTRAP_RESAMPLES = 2000
SEED = 1234

for _d in (DATA_DIR, OUTPUT_DIR, RESULTS_DIR):
    os.makedirs(_d, exist_ok=True)


# ---------------------------------------------------------------- hashing

def sha256_lines(lines) -> str:
    """Fingerprint of an evaluation set: any edit or reordering changes it."""
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def environment() -> dict:
    info = {"python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform()}
    for mod in ("torch", "transformers", "sacrebleu"):
        try:
            info[mod] = __import__(mod).__version__
        except Exception:
            pass
    return info


def write_report(name: str, report: dict) -> str:
    report = {"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "command": " ".join([os.path.basename(sys.executable)] + sys.argv), **report}
    path = os.path.join(RESULTS_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=lambda o: round(float(o), 6))  # numpy scalars
    return path


# --------------------------------------------------- Kikamba text normalizer
#
# Applied identically to reference and hypothesis before character/word error
# rates are computed (speech-to-text and voice round-trip evaluations).
#
#   K0  NFC, lowercase, punctuation -> space, collapse whitespace. Keeps the
#       apostrophe (it is orthographic in Kikamba: ng'ombe, kw'o) and the
#       tilde vowels ĩ/ũ.
#   K1  K0 + drop diacritics (ĩ->i, ũ->u). The ASR model under test writes
#       no tildes at all, so K0 would charge it for every ĩ/ũ; K1 measures
#       recognition rather than diacritic spelling. We report both.

_PUNCT = re.compile(r"[.,;:?!\"“”‘«»()\[\]{}/\\\-–—…]")
_APOSTROPHES = str.maketrans({"’": "'", "`": "'", "´": "'", "ʼ": "'"})


def normalize_k0(text: str) -> str:
    t = unicodedata.normalize("NFC", text).translate(_APOSTROPHES).lower()
    t = _PUNCT.sub(" ", t)
    return " ".join(t.split())


def normalize_k1(text: str) -> str:
    t = unicodedata.normalize("NFD", normalize_k0(text))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return unicodedata.normalize("NFC", t)


NORMALIZERS = {"K0": normalize_k0, "K1": normalize_k1}


# ------------------------------------------------------------ edit distance

def levenshtein(a, b) -> int:
    """Unit-cost Levenshtein distance over sequences (chars or words)."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def error_counts(refs, hyps, tier: str):
    """Per-item (char errors, char length, word errors, word length) after normalization."""
    norm = NORMALIZERS[tier]
    rows = []
    for r, h in zip(refs, hyps):
        r, h = norm(r), norm(h)
        rows.append((levenshtein(list(r), list(h)), len(r), levenshtein(r.split(), h.split()), len(r.split())))
    return np.array(rows, dtype=np.int64).reshape(-1, 4)


# ------------------------------------------------------- bootstrap statistics

def corpus_rate(num, den) -> float:
    return float(num.sum() / max(1, den.sum()))


def bootstrap_ci(num, den, seed: int = SEED, b: int = BOOTSTRAP_RESAMPLES):
    """95% CI of a corpus-level error rate (sum of errors / sum of lengths),
    resampling items with replacement (Bisani & Ney 2004)."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(num), size=(b, len(num)))
    rates = num[idx].sum(axis=1) / np.maximum(1, den[idx].sum(axis=1))
    return [float(np.percentile(rates, 2.5)), float(np.percentile(rates, 97.5))]


def paired_test(num_a, den_a, num_b, den_b, seed: int = SEED, b: int = BOOTSTRAP_RESAMPLES) -> dict:
    """One-sided paired bootstrap: is system A's error rate lower than B's?
    Both systems are resampled on the same item indices each iteration."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(num_a), size=(b, len(num_a)))
    a = num_a[idx].sum(axis=1) / np.maximum(1, den_a[idx].sum(axis=1))
    bb = num_b[idx].sum(axis=1) / np.maximum(1, den_b[idx].sum(axis=1))
    delta = a - bb  # < 0 means A is better (lower error)
    return {
        "delta_median": float(np.median(delta)),
        "delta_ci95": [float(np.percentile(delta, 2.5)), float(np.percentile(delta, 97.5))],
        "p_value_one_sided": float(np.mean(delta >= 0)),  # probability A is NOT better
    }


def protocol_block(**extra) -> dict:
    return {
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "seed": SEED,
        "ci": "95% bootstrap over items (Bisani & Ney 2004); paired for system comparisons",
        "environment": environment(),
        **extra,
    }
