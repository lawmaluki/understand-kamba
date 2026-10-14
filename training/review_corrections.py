"""
Turn translation corrections from the app into training pairs, with a human
review step in between (users can type anything, so nothing is trained on
until a Kikamba speaker has approved it).

1. Download new corrections into a review sheet:
       python training/review_corrections.py export
   -> training/data/review/corrections-<date>.tsv
   Needs HF_TOKEN (a token that can read the private corrections dataset).

2. Open the sheet (Excel / Google Sheets / LibreOffice). For each row, put
   `y` in the `approve` column if the correction is right, `n` if not. You may
   fix the `correction` text. Save it as TSV (tab-separated) again.

3. Import the approved rows as training pairs:
       python training/review_corrections.py import training/data/review/corrections-<date>.tsv
   -> training/data/community/corrections-<date>.tsv (kam / eng columns), which
   training/build_parallel.py merges in. Then rerun the fine-tuning notebook.

Rows already exported once are remembered in training/data/review/seen_ids.txt.
"""
import argparse
import csv
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.join(HERE, "data", "review")
COMMUNITY = os.path.join(HERE, "data", "community")
SEEN = os.path.join(REVIEW, "seen_ids.txt")
DEFAULT_REPO = "lawmaluki/kamba-translation-corrections"
COLUMNS = ["approve", "direction", "source", "model_translation", "correction", "origin", "dialect", "time", "id"]


def export(repo: str):
    from huggingface_hub import snapshot_download

    path = snapshot_download(repo_id=repo, repo_type="dataset", allow_patterns=["data/*/corrections.jsonl"])
    rows = []
    for f in sorted(glob.glob(os.path.join(path, "data", "*", "corrections.jsonl"))):
        with open(f, encoding="utf-8") as fh:
            rows += [json.loads(line) for line in fh if line.strip()]
    seen = set(open(SEEN, encoding="utf-8").read().split()) if os.path.exists(SEEN) else set()
    new = sorted((r for r in rows if r["id"] not in seen), key=lambda r: r["time"])
    if not new:
        print(f"No new corrections ({len(rows)} in total, all exported before).")
        return
    os.makedirs(REVIEW, exist_ok=True)
    out = os.path.join(REVIEW, f"corrections-{time.strftime('%Y%m%d-%H%M')}.tsv")
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in new:
            w.writerow({**r, "approve": ""})
    with open(SEEN, "a", encoding="utf-8") as fh:
        fh.writelines(r["id"] + "\n" for r in new)
    print(f"{len(new)} new corrections -> {out}\nMark each row y/n in the 'approve' column, then run the import step.")


def import_reviewed(sheet: str):
    with open(sheet, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    approved = [r for r in rows if r.get("approve", "").strip().lower() in ("y", "yes")]
    undecided = sum(1 for r in rows if not r.get("approve", "").strip())
    if undecided:
        print(f"Note: {undecided} rows have no y/n yet and are skipped.")
    os.makedirs(COMMUNITY, exist_ok=True)
    out = os.path.join(COMMUNITY, os.path.basename(sheet))
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["kam", "eng"])
        for r in approved:
            # The Kikamba side is the source for kam_to_en and the correction for en_to_kam.
            kam, eng = (r["source"], r["correction"]) if r["direction"] == "kam_to_en" else (r["correction"], r["source"])
            w.writerow([kam.strip(), eng.strip()])
    print(f"{len(approved)} approved pairs -> {out}\nNext: python training/build_parallel.py, then rerun the fine-tuning notebook.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export", help="download new corrections into a review sheet")
    e.add_argument("--repo", default=os.getenv("CORRECTIONS_DATASET_REPO", DEFAULT_REPO))
    i = sub.add_parser("import", help="turn approved rows of a review sheet into training pairs")
    i.add_argument("sheet")
    args = ap.parse_args()
    if args.cmd == "export":
        export(args.repo)
    else:
        if not os.path.exists(args.sheet):
            sys.exit(f"not found: {args.sheet}")
        import_reviewed(args.sheet)
