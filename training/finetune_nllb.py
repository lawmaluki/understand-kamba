"""
Fine-tune NLLB-200 for English <-> Kikamba with LoRA, using only existing data,
and compare it with the untouched model. Meant for a free 16 GB GPU (Kaggle or
Colab T4); see training/finetune_kaggle.ipynb.

Steps
  1. Data: the clean human pairs (training/data/kam_eng.tsv) and the filtered
     OPUS-NLLB pairs (training/data/opus_filtered.tsv.gz). 10 whole stories are
     held out as an everyday test set; FLORES-200 devtest is the second test set.
  2. Alignment filter: the base model scores every OPUS pair in both directions
     (dual conditional cross-entropy, Junczys-Dowmunt 2018); the worst-matched
     pairs are dropped.
  3. LoRA fine-tuning on both directions at once; clean pairs are repeated.
  4. Evaluation: base vs fine-tuned, chrF++ on both test sets and both directions,
     decoding exactly as the app does (app/translate.py: beam 5, no-repeat 4).
  5. The merged model is saved to --out, ready to upload to the Hugging Face Hub.

    python training/finetune_nllb.py --model facebook/nllb-200-distilled-1.3B --out nllb-kam-ft
"""
import argparse
import csv
import gzip
import json
import os
import random
import sys
import time
import urllib.request

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "1")

from app.translate import nllb_generate  # noqa: E402  (same decoding as the app)

KAM, ENG = "kam_Latn", "eng_Latn"
FLORES_URL = ("https://raw.githubusercontent.com/kithyadan/kikamba-corpus/"
              "961744532eeacbfeba1fa67b4eaede3f47633485/data/parallel/flores200.jsonl")
SEED = 1234
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- data

def load_data(n_test_stories: int):
    with open(os.path.join(HERE, "data", "kam_eng.tsv"), encoding="utf-8") as f:
        clean = list(csv.DictReader(f, delimiter="\t"))
    stories = sorted({r["doc"] for r in clean if r["source"] == "glotstorybook"})
    test_docs = set(random.Random(SEED).sample(stories, n_test_stories))
    story_test = [(r["kam"], r["eng"]) for r in clean if r["doc"] in test_docs]
    clean_train = [(r["kam"], r["eng"]) for r in clean if r["doc"] not in test_docs]

    with gzip.open(os.path.join(HERE, "data", "opus_filtered.tsv.gz"), "rt", encoding="utf-8") as f:
        opus = [(r["kam"], r["eng"]) for r in csv.DictReader(f, delimiter="\t")]

    with urllib.request.urlopen(FLORES_URL, timeout=60) as r:
        rows = [json.loads(x) for x in r.read().decode("utf-8").splitlines() if x.strip()]
    flores_test = [(x["text"], x["translation"]) for x in rows
                   if x["translation_lang"] == "eng" and (x.get("extra") or {}).get("flores_split") == "devtest"]
    return clean_train, opus, story_test, flores_test


# ---------------------------------------------------------------- alignment scoring

@torch.no_grad()
def pair_losses(model, tok, pairs, src_lang, tgt_lang, batch=32):
    """Mean per-token cross-entropy of target given source, per pair."""
    out = []
    tok.src_lang, tok.tgt_lang = src_lang, tgt_lang
    for i in range(0, len(pairs), batch):
        src = [p[0] for p in pairs[i:i + batch]]
        tgt = [p[1] for p in pairs[i:i + batch]]
        enc = tok(src, text_target=tgt, return_tensors="pt", padding=True, truncation=True, max_length=128).to(DEVICE)
        labels = enc["labels"].masked_fill(enc["labels"] == tok.pad_token_id, -100)
        with torch.autocast("cuda", dtype=torch.float16, enabled=DEVICE == "cuda"):
            logits = model(input_ids=enc["input_ids"], attention_mask=enc["attention_mask"], labels=labels).logits
        nll = torch.nn.functional.cross_entropy(logits.float().transpose(1, 2), labels, reduction="none")
        mask = (labels != -100).float()
        out += ((nll * mask).sum(1) / mask.sum(1)).tolist()
    return out


def filter_by_alignment(model, tok, opus, keep_frac):
    """Dual conditional cross-entropy: keep pairs that translate well in BOTH directions
    and about equally well (a big gap means one side has content the other lacks)."""
    k2e = pair_losses(model, tok, opus, KAM, ENG)
    e2k = pair_losses(model, tok, [(e, k) for k, e in opus], ENG, KAM)
    score = [abs(a - b) + 0.5 * (a + b) for a, b in zip(k2e, e2k)]
    order = sorted(range(len(opus)), key=lambda i: score[i])
    kept = [opus[i] for i in order[:int(len(opus) * keep_frac)]]
    log(f"alignment filter kept {len(kept):,}/{len(opus):,} OPUS pairs")
    return kept


# ---------------------------------------------------------------- training

class PairDataset(torch.utils.data.Dataset):
    """Each (kam, eng) pair becomes two examples, one per direction."""

    def __init__(self, tok, pairs, max_len=128):
        self.items = []
        for kam, eng in pairs:
            for s, t, sl, tl in ((kam, eng, KAM, ENG), (eng, kam, ENG, KAM)):
                tok.src_lang, tok.tgt_lang = sl, tl
                enc = tok(s, text_target=t, truncation=True, max_length=max_len)
                self.items.append(enc)
        random.Random(SEED).shuffle(self.items)

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        return self.items[i]


def train(model, tok, pairs, args):
    from peft import LoraConfig, get_peft_model
    from transformers import DataCollatorForSeq2Seq, Seq2SeqTrainer, Seq2SeqTrainingArguments

    model = get_peft_model(model, LoraConfig(
        r=args.lora_r, lora_alpha=2 * args.lora_r, lora_dropout=0.05, task_type="SEQ_2_SEQ_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "out_proj", "fc1", "fc2"]))
    model.print_trainable_parameters()
    data = PairDataset(tok, pairs)
    log(f"training on {len(data):,} examples ({len(pairs):,} pairs x 2 directions)")
    steps = -(-len(data) // (args.batch * args.grad_accum)) * args.epochs
    warmup = max(1, int(0.05 * (args.max_steps if args.max_steps > 0 else steps)))  # int: works on transformers 4 and 5
    trainer = Seq2SeqTrainer(
        model=model,
        args=Seq2SeqTrainingArguments(
            output_dir=os.path.join(args.out, "checkpoints"), per_device_train_batch_size=args.batch,
            gradient_accumulation_steps=args.grad_accum, learning_rate=args.lr, num_train_epochs=args.epochs,
            warmup_steps=warmup, lr_scheduler_type="cosine", fp16=DEVICE == "cuda", max_steps=args.max_steps, logging_steps=50, save_strategy="no",
            report_to=[], seed=SEED),
        train_dataset=data,
        data_collator=DataCollatorForSeq2Seq(tok, model=model, padding=True),
    )
    trainer.train()
    return model.merge_and_unload()


# ---------------------------------------------------------------- evaluation

def translate(model, tok, sentences, src, tgt, batch=16):
    out = []
    for i in range(0, len(sentences), batch):
        out += nllb_generate(model, tok, sentences[i:i + batch], src, tgt, device=DEVICE)
    return out


def evaluate(model, tok, tests, label):
    from sacrebleu.metrics import CHRF

    model.eval()
    scores, outputs = {}, {}
    for name, pairs in tests.items():
        kam, eng = [p[0] for p in pairs], [p[1] for p in pairs]
        for direction, src, refs, sl, tl in (("kam_to_en", kam, eng, KAM, ENG), ("en_to_kam", eng, kam, ENG, KAM)):
            hyps = translate(model, tok, src, sl, tl)
            scores[f"{name}/{direction}"] = round(CHRF(word_order=2).corpus_score(hyps, [refs]).score, 2)
            outputs[f"{name}/{direction}"] = hyps
            log(f"[{label}] {name} {direction}: chrF++ {scores[f'{name}/{direction}']}")
    return scores, outputs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="facebook/nllb-200-distilled-1.3B")
    ap.add_argument("--out", default="nllb-kam-ft")
    ap.add_argument("--keep-frac", type=float, default=0.6, help="share of OPUS pairs kept by the alignment filter")
    ap.add_argument("--clean-repeat", type=int, default=3, help="how often the clean human pairs are repeated")
    ap.add_argument("--test-stories", type=int, default=10)
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--grad-accum", type=int, default=2)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--skip-base-eval", action="store_true")
    ap.add_argument("--max-steps", type=int, default=-1)
    ap.add_argument("--smoke", action="store_true", help="tiny run on CPU to check the pipeline works")
    args = ap.parse_args()

    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    random.seed(SEED)
    torch.manual_seed(SEED)
    os.makedirs(args.out, exist_ok=True)
    clean_train, opus, story_test, flores_test = load_data(args.test_stories)
    log(f"clean train {len(clean_train)}, OPUS {len(opus):,}, story test {len(story_test)}, FLORES devtest {len(flores_test)}")
    if args.smoke:
        clean_train, opus, story_test, flores_test = clean_train[:8], opus[:16], story_test[:3], flores_test[:3]
        args.max_steps = 2
    tests = {"stories": story_test, "flores_devtest": flores_test}

    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model).to(DEVICE)

    report = {"args": vars(args)}
    if not args.skip_base_eval:
        report["base"], _ = evaluate(model, tok, tests, "base")
    opus_kept = filter_by_alignment(model, tok, opus, args.keep_frac)
    model = train(model, tok, clean_train * args.clean_repeat + opus_kept, args)
    report["finetuned"], outputs = evaluate(model, tok, tests, "fine-tuned")

    model.save_pretrained(args.out)
    tok.save_pretrained(args.out)
    with open(os.path.join(args.out, "eval_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    with open(os.path.join(args.out, "test_outputs.json"), "w", encoding="utf-8") as f:
        json.dump({"tests": tests, "outputs": outputs}, f, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"{'test set / direction':32} {'base':>8} {'fine-tuned':>11}")
    for k, v in report["finetuned"].items():
        b = report.get("base", {}).get(k)
        print(f"{k:32} {'-' if b is None else f'{b:.2f}':>8} {v:11.2f}  {'' if b is None else f'{v - b:+.2f}'}")
    print(f"\nModel saved to {args.out}/. Deploy it only if it beats the base model on BOTH test sets.")


if __name__ == "__main__":
    main()
