"""
Speech-to-text evaluation on the FLEURS Kamba (kam_ke) test split
(827 read utterances of 346 FLORES sentences, 3.73 h).

Systems (greedy CTC decoding, float32 on CPU or GPU):
  farmerline  FarmerlineML/w2v-bert-2.0_kamba (the app's model)
  mms         facebook/mms-1b-all with its Kamba ('kam') adapter

Metrics: CER (primary) and WER, corpus-level, at normalization tiers K0 and
K1 (eval/common.py), with 95% bootstrap CIs, a paired test between the two
systems, and per-gender breakdowns.

    python eval/asr_eval.py --system farmerline     # transcribe (resumable)
    python eval/asr_eval.py --system mms
    python eval/asr_eval.py --score                 # score whatever is complete
"""
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (DATA_DIR, OUTPUT_DIR, bootstrap_ci, corpus_rate, error_counts, paired_test,  # noqa: E402
                    protocol_block, sha256_lines, write_report)

SYSTEMS = {
    "farmerline": ("FarmerlineML/w2v-bert-2.0_kamba", None),
    "mms": ("facebook/mms-1b-all", "kam"),
}
FLEURS = os.path.join(DATA_DIR, "fleurs_kam")
OUT = os.path.join(OUTPUT_DIR, "asr")
os.makedirs(OUT, exist_ok=True)


def test_items():
    with open(os.path.join(FLEURS, "test.tsv"), encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def transcribe(system: str, device: str):
    import soundfile as sf
    import torch
    from transformers import AutoModelForCTC, AutoProcessor

    model_id, lang = SYSTEMS[system]
    kwargs = {"target_lang": lang} if lang else {}
    processor = AutoProcessor.from_pretrained(model_id, **kwargs)
    model = AutoModelForCTC.from_pretrained(model_id, **({**kwargs, "ignore_mismatched_sizes": True} if lang else {}))
    if lang:
        model.load_adapter(lang)
    model.to(device).eval()
    torch.set_num_threads(os.cpu_count() or 4)

    items = test_items()
    path = os.path.join(OUT, f"{system}.tsv")
    done = set()
    if os.path.exists(path):
        done = {r["file"] for r in csv.DictReader(open(path, encoding="utf-8"), delimiter="\t")}
    new = not os.path.exists(path)
    t0 = time.time()
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        if new:
            w.writerow(["file", "hypothesis"])
        for n, it in enumerate(items, 1):
            if it["file"] in done:
                continue
            audio, sr = sf.read(os.path.join(FLEURS, "test", it["file"]), dtype="float32")
            inputs = processor(audio, sampling_rate=sr, return_tensors="pt").to(device)
            with torch.inference_mode():
                ids = torch.argmax(model(**inputs).logits, dim=-1)[0].cpu()
            w.writerow([it["file"], processor.decode(ids).strip()])
            f.flush()
            if n % 50 == 0:
                print(f"[{system}] {n}/{len(items)}  {(time.time() - t0) / n:.2f}s/utt", flush=True)
    print(f"[{system}] done", flush=True)


def score():
    items = test_items()
    refs = [it["text"] for it in items]
    by_file = {it["file"]: it for it in items}
    report = {"test_set": "FLEURS kam_ke test", "n_utterances": len(items),
              "references_sha256": sha256_lines([it["file"] + "\t" + it["text"] for it in items]),
              "protocol": protocol_block(primary_metric="CER", secondary_metric="WER", decoding="greedy CTC",
                                         normalizers="K0 (NFC, lowercase, punctuation->space; keeps ' and ĩ/ũ); "
                                                     "K1 = K0 + drop diacritics"),
              "systems": {}, "paired": {}}
    counts = {}
    for system in SYSTEMS:
        path = os.path.join(OUT, f"{system}.tsv")
        if not os.path.exists(path):
            continue
        hyp = {r["file"]: r["hypothesis"] for r in csv.DictReader(open(path, encoding="utf-8"), delimiter="\t")}
        if len(hyp) < len(items):
            print(f"skip {system}: {len(hyp)}/{len(items)} transcribed")
            continue
        hyps = [hyp[it["file"]] for it in items]
        sysrep = {}
        for tier in ("K0", "K1"):
            c = error_counts(refs, hyps, tier)
            counts[(system, tier)] = c
            sysrep[tier] = {
                "cer": round(corpus_rate(c[:, 0], c[:, 1]), 4), "cer_ci95": [round(x, 4) for x in bootstrap_ci(c[:, 0], c[:, 1])],
                "wer": round(corpus_rate(c[:, 2], c[:, 3]), 4), "wer_ci95": [round(x, 4) for x in bootstrap_ci(c[:, 2], c[:, 3], seed=1235)],
            }
            for g in ("FEMALE", "MALE"):
                mask = [by_file[it["file"]]["gender"] == g for it in items]
                cg = c[mask]
                sysrep[tier][f"cer_{g.lower()}"] = round(corpus_rate(cg[:, 0], cg[:, 1]), 4)
                sysrep[tier][f"cer_{g.lower()}_ci95"] = [round(x, 4) for x in bootstrap_ci(cg[:, 0], cg[:, 1], seed=1236)]
                sysrep[tier][f"n_{g.lower()}"] = int(sum(mask))
        report["systems"][system] = sysrep
    if ("farmerline", "K1") in counts and ("mms", "K1") in counts:
        for tier in ("K0", "K1"):
            a, b = counts[("farmerline", tier)], counts[("mms", tier)]
            report["paired"][f"farmerline_vs_mms_{tier}_cer"] = paired_test(a[:, 0], a[:, 1], b[:, 0], b[:, 1])
    path = write_report("asr_fleurs_test", report)
    for s, r in report["systems"].items():
        for tier, v in r.items():
            print(f"{s:11} {tier}  CER {v['cer']:.4f} {v['cer_ci95']}  WER {v['wer']:.4f} {v['wer_ci95']}  "
                  f"F {v['cer_female']:.4f} (n={v['n_female']})  M {v['cer_male']:.4f} (n={v['n_male']})")
    for k, v in report["paired"].items():
        print(k, v)
    print("report:", path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", choices=list(SYSTEMS))
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--device", default="cpu", help="cpu or cuda")
    args = ap.parse_args()
    if args.system:
        transcribe(args.system, args.device)
    if args.score:
        score()
