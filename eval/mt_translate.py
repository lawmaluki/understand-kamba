"""
Translate FLORES-200 devtest with one system, writing one output line per
input line to eval/outputs/mt/<system>.<direction>.txt. Re-running resumes
where a previous run stopped.

Systems (decoding identical to the app: sentence split, beam 5,
no_repeat_ngram_size 4, output capped at 2x input + 16 tokens -- see
app/translate.py):
  nllb-600m   facebook/nllb-200-distilled-600M on local CPU
  nllb-1.3b   facebook/nllb-200-distilled-1.3B on local CPU
  nllb-3.3b   facebook/nllb-200-3.3B, float16 on the Hugging Face Space's
              ZeroGPU, through its /translate API. Each response names the
              model that answered; the run stops if the Space falls back to
              its CPU model, so outputs are never mixed.

    python eval/mt_translate.py --system nllb-600m --direction both
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA_DIR, OUTPUT_DIR, REPO_DIR  # noqa: E402

os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "1")
sys.path.insert(0, REPO_DIR)

LOCAL = {"nllb-600m": "facebook/nllb-200-distilled-600M", "nllb-1.3b": "facebook/nllb-200-distilled-1.3B",
         "nllb-3.3b-local": "facebook/nllb-200-3.3B"}  # the last only for the precision/API control
SPACE = {"nllb-3.3b": ("https://lawmaluki-understand-kamba-api.hf.space", "facebook/nllb-200-3.3B")}
DIRECTIONS = {
    "en_to_kam": ("eng_Latn", "kam_Latn"),
    "kam_to_en": ("kam_Latn", "eng_Latn"),
}
OUT = os.path.join(OUTPUT_DIR, "mt")
os.makedirs(OUT, exist_ok=True)


def source_lines(direction: str) -> list[str]:
    src = DIRECTIONS[direction][0]
    return open(os.path.join(DATA_DIR, "flores200", f"{src}.devtest"), encoding="utf-8").read().splitlines()


def done_lines(path: str) -> int:
    return len(open(path, encoding="utf-8").read().splitlines()) if os.path.exists(path) else 0


def run_local(system: str, directions: list[str], batch: int, device: str, dtype: str, limit: int | None):
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    from app.translate import nllb_generate, split_sentences

    torch.set_num_threads(os.cpu_count() or 4)
    tok = AutoTokenizer.from_pretrained(LOCAL[system])
    # float32 by default on either device, so CPU and GPU runs produce the same outputs;
    # float16 only for the precision control (the Space runs 3.3B in float16).
    model = AutoModelForSeq2SeqLM.from_pretrained(LOCAL[system], dtype=getattr(torch, dtype)).to(device).eval()
    tag = system + ("-fp16" if dtype == "float16" else "")
    for direction in directions:
        src_code, tgt_code = DIRECTIONS[direction]
        lines = source_lines(direction)[:limit]
        path = os.path.join(OUT, f"{tag}.{direction}.txt")
        start = done_lines(path)
        t0 = time.time()
        with open(path, "a", encoding="utf-8") as f:
            for i in range(start, len(lines), batch):
                chunk = lines[i:i + batch]
                # As in the app: each line is split into sentences, translated, re-joined.
                pieces = [split_sentences(line) or [line] for line in chunk]
                flat = [s for p in pieces for s in p]
                out = iter(nllb_generate(model, tok, flat, src_code, tgt_code, device=device))
                for p in pieces:
                    f.write(" ".join(next(out) for _ in p).replace("\n", " ") + "\n")
                f.flush()
                n = i + len(chunk)
                print(f"[{system} {direction}] {n}/{len(lines)}  {(time.time() - t0) / max(1, n - start):.2f}s/line", flush=True)


def run_space(system: str, directions: list[str]):
    import httpx

    base, expected = SPACE[system]
    key = {"en_to_kam": "translation_kam", "kam_to_en": "translation_en"}
    client = httpx.Client(timeout=300)
    for direction in directions:
        lines = source_lines(direction)
        path = os.path.join(OUT, f"{system}.{direction}.txt")
        start = done_lines(path)
        with open(path, "a", encoding="utf-8") as f:
            for i in range(start, len(lines)):
                for attempt in range(5):
                    try:
                        r = client.post(f"{base}/translate", json={"text": lines[i], "direction": direction})
                        r.raise_for_status()
                        break
                    except Exception as e:
                        print(f"  retry {attempt + 1} after error: {e}", flush=True)
                        time.sleep(20 * (attempt + 1))
                else:
                    sys.exit(f"[{system} {direction}] giving up at line {i}")
                data = r.json()
                if data.get("model") != expected:
                    sys.exit(f"[{system} {direction}] line {i}: answered by {data.get('model')!r}, not {expected} "
                             "(GPU quota likely used up). Stopping; re-run later to resume.")
                f.write(data[key[direction]].replace("\n", " ") + "\n")
                f.flush()
                if (i + 1) % 25 == 0:
                    print(f"[{system} {direction}] {i + 1}/{len(lines)}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True, choices=sorted(LOCAL) + sorted(SPACE))
    ap.add_argument("--direction", default="both", choices=["both", *DIRECTIONS])
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--device", default="cpu", help="cpu or cuda (local systems only)")
    ap.add_argument("--dtype", default="float32", choices=["float32", "float16"], help="local systems only")
    ap.add_argument("--limit", type=int, help="translate only the first N lines (controls)")
    args = ap.parse_args()
    dirs = list(DIRECTIONS) if args.direction == "both" else [args.direction]
    if args.system in LOCAL:
        run_local(args.system, dirs, args.batch, args.device, args.dtype, args.limit)
    else:
        run_space(args.system, dirs)
    print("done", flush=True)
