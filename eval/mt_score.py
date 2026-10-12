"""
Score the translation outputs in eval/outputs/mt/ against FLORES-200 devtest:
chrF++ (primary) and BLEU (secondary), each with a 95% bootstrap confidence
interval, plus paired significance tests of every system against the
baseline (NLLB-600M, the app's original model).

English -> Kikamba is scored at two tiers, applied identically to every
system and to the references:
  T0  raw text.
  T1  tilde-insensitive: ĩ->i, ũ->u on both sides. 65% of the FLORES Kamba
      reference sentences are written without the tilde vowels while the
      models usually write them, so T0 charges a spelling convention, not a
      translation error. We report both and never T1 alone.

    python eval/mt_score.py
"""
import os
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BOOTSTRAP_RESAMPLES, DATA_DIR, OUTPUT_DIR, SEED, protocol_block, sha256_lines, write_report  # noqa: E402

os.environ["SACREBLEU_SEED"] = str(SEED)  # sacrebleu reads its bootstrap seed from here
from sacrebleu.metrics import BLEU, CHRF  # noqa: E402
from sacrebleu.significance import PairedTest  # noqa: E402

SYSTEMS = ["nllb-600m", "nllb-1.3b", "nllb-3.3b"]
BASELINE = "nllb-600m"
LANGS = {"en_to_kam": ("eng_Latn", "kam_Latn"), "kam_to_en": ("kam_Latn", "eng_Latn")}


def fold_tildes(s: str) -> str:
    s = unicodedata.normalize("NFD", unicodedata.normalize("NFC", s))
    s = s.replace("̃", "")  # combining tilde (ĩ = i + U+0303, ũ = u + U+0303)
    return unicodedata.normalize("NFC", s)


TIERS = {"T0": lambda s: s, "T1": fold_tildes}


def controls() -> dict:
    """English->Kikamba checks that the 3.3B result is not an artefact of float16 or of the API:
    600M in float16 vs float32 (full devtest), and 3.3B in float16 run locally vs through the
    Space (first 100 lines)."""
    def read(name, n=None):
        path = os.path.join(OUTPUT_DIR, "mt", f"{name}.en_to_kam.txt")
        return open(path, encoding="utf-8").read().splitlines()[:n] if os.path.exists(path) else None

    refs = open(os.path.join(DATA_DIR, "flores200", "kam_Latn.devtest"), encoding="utf-8").read().splitlines()
    chrf = lambda h, r: round(CHRF(word_order=2).corpus_score(h, [r]).score, 2)  # noqa: E731
    out = {}
    a, b = read("nllb-600m"), read("nllb-600m-fp16")
    if a and b and len(b) == len(refs):
        out["600m_fp32_vs_fp16"] = {"n": len(refs), "chrf++_fp32": chrf(a, refs), "chrf++_fp16": chrf(b, refs),
                                    "identical_outputs": sum(x == y for x, y in zip(a, b))}
    local = read("nllb-3.3b-local-fp16")
    if local:
        n = len(local)
        space = read("nllb-3.3b", n)
        out["3.3b_local_vs_space"] = {"n": n, "chrf++_space": chrf(space, refs[:n]), "chrf++_local": chrf(local, refs[:n]),
                                      "chrf++_600m": chrf(read("nllb-600m", n), refs[:n]),
                                      "identical_outputs": sum(x == y for x, y in zip(local, space))}
    for k, v in out.items():
        print(k, v)
    return out


def main():
    report = {"test_set": "FLORES-200 devtest", "protocol": protocol_block(
        primary_metric="chrF++ (sacrebleu CHRF word_order=2)", secondary_metric="BLEU (sacrebleu default 13a)",
        sacrebleu_bootstrap="corpus_score(n_bootstrap=2000), SACREBLEU_SEED=1234",
        paired_test="sacrebleu PairedTest, paired bootstrap resampling (test_type='bs', n_samples=2000)",
        decoding="beam 5, no_repeat_ngram_size 4, max_new_tokens = 2 x input + 16, sentence-split as in app/translate.py",
    ), "directions": {}}
    table = []
    for direction, (src, tgt) in LANGS.items():
        refs = open(os.path.join(DATA_DIR, "flores200", f"{tgt}.devtest"), encoding="utf-8").read().splitlines()
        systems = {}
        for s in SYSTEMS:
            path = os.path.join(OUTPUT_DIR, "mt", f"{s}.{direction}.txt")
            if os.path.exists(path):
                hyps = open(path, encoding="utf-8").read().splitlines()
                if len(hyps) == len(refs):
                    systems[s] = hyps
                else:
                    print(f"skip {s} {direction}: {len(hyps)}/{len(refs)} lines")
        tiers = ["T0", "T1"] if tgt == "kam_Latn" else ["T0"]
        entry = {"references_sha256": sha256_lines(refs), "n": len(refs), "tiers": {}}
        for tier in tiers:
            f = TIERS[tier]
            r = [f(x) for x in refs]
            res = {}
            for s, hyps in systems.items():
                h = [f(x) for x in hyps]
                chrf = CHRF(word_order=2).corpus_score(h, [r], n_bootstrap=BOOTSTRAP_RESAMPLES)
                bleu = BLEU().corpus_score(h, [r], n_bootstrap=BOOTSTRAP_RESAMPLES)
                res[s] = {
                    "chrf++": round(chrf.score, 2), "chrf++_ci95": [round(float(chrf.score - chrf._ci), 2), round(float(chrf.score + chrf._ci), 2)],
                    "bleu": round(bleu.score, 2), "bleu_ci95": [round(float(bleu.score - bleu._ci), 2), round(float(bleu.score + bleu._ci), 2)],
                    "output_sha256": sha256_lines(hyps),
                }
            # Paired bootstrap p-values are for "the difference is due to chance", whichever
            # system is ahead: read them together with the sign of the score difference.
            for base, key in ((BASELINE, "p_vs_baseline"), ("nllb-1.3b", "p_vs_1.3b")):
                others = [s for s in systems if s != base and not (base == "nllb-1.3b" and s == BASELINE)]
                if base not in systems or not others:
                    continue
                named = [(base, [f(x) for x in systems[base]])] + [(s, [f(x) for x in systems[s]]) for s in others]
                pt = PairedTest(named, {"chrF++": CHRF(word_order=2)}, [r], test_type="bs", n_samples=BOOTSTRAP_RESAMPLES)
                _, scores = pt()  # keyed by "System" and the metric's own name ("chrF2++")
                metric_key = next(k for k in scores if k != "System")
                for name, s_results in zip(scores["System"], scores[metric_key]):
                    if name != base and name in res:
                        res[name][key] = float(s_results.p_value)
            entry["tiers"][tier] = res
            for s, v in res.items():
                table.append((direction, tier, s, v))
        report["directions"][direction] = entry

    report["controls"] = controls()
    path = write_report("mt_flores_devtest", report)
    print(f"\n{'direction':10} {'tier':4} {'system':10} {'chrF++':>7} {'95% CI':>15} {'BLEU':>6} {'95% CI':>15} {'p vs 600M':>9}")
    for direction, tier, s, v in table:
        p = v.get("p_vs_baseline")
        print(f"{direction:10} {tier:4} {s:10} {v['chrf++']:7.2f} {str(v['chrf++_ci95']):>15} {v['bleu']:6.2f} "
              f"{str(v['bleu_ci95']):>15} {'' if p is None else f'{p:.4f}':>9}")
    print("\nreport:", path)


if __name__ == "__main__":
    main()
