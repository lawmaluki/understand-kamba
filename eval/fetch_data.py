"""
Download the public test sets into eval/data/ (not committed) and print
their fingerprints.

- FLORES-200 (Meta, CC-BY-SA 4.0): kam_Latn / eng_Latn, dev + devtest.
  Professional translations; devtest (1,012 sentences) is the translation test set.
- FLEURS (Google, CC-BY 4.0): Kamba (kam_ke) test split -- read speech of
  FLORES sentences, used for speech-to-text and as real-speaker reference audio.

    python eval/fetch_data.py            # FLORES only
    python eval/fetch_data.py --fleurs   # also FLEURS Kamba test audio (~730 MB)
"""
import argparse
import csv
import io
import os
import sys
import tarfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA_DIR, sha256_lines  # noqa: E402

FLORES_URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"


def fetch_flores():
    out = os.path.join(DATA_DIR, "flores200")
    os.makedirs(out, exist_ok=True)
    wanted = {f"flores200_dataset/{split}/{lang}.{split}" for split in ("dev", "devtest") for lang in ("kam_Latn", "eng_Latn")}
    if all(os.path.exists(os.path.join(out, os.path.basename(w))) for w in wanted):
        print("FLORES-200: already downloaded")
    else:
        print("FLORES-200: downloading ...")
        data = urllib.request.urlopen(FLORES_URL, timeout=300).read()
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            for m in tar.getmembers():
                if m.name.removeprefix("./") in wanted:  # archive paths start with "./"
                    with open(os.path.join(out, os.path.basename(m.name)), "wb") as f:
                        f.write(tar.extractfile(m).read())
    for name in sorted(os.listdir(out)):
        lines = open(os.path.join(out, name), encoding="utf-8").read().splitlines()
        print(f"  {name:22} {len(lines):5} lines  sha256 {sha256_lines(lines)}")


def fetch_fleurs():
    from huggingface_hub import hf_hub_download

    out = os.path.join(DATA_DIR, "fleurs_kam")
    audio_dir = os.path.join(out, "test")
    os.makedirs(audio_dir, exist_ok=True)
    tsv = hf_hub_download("google/fleurs", "data/kam_ke/test.tsv", repo_type="dataset")
    rows = list(csv.reader(open(tsv, encoding="utf-8"), delimiter="\t"))
    if len(os.listdir(audio_dir)) < len(rows):
        print("FLEURS kam_ke test: downloading audio (~730 MB) ...")
        tgz = hf_hub_download("google/fleurs", "data/kam_ke/audio/test.tar.gz", repo_type="dataset")
        with tarfile.open(tgz) as tar:
            for m in tar.getmembers():
                if m.isfile() and m.name.endswith(".wav"):
                    with open(os.path.join(audio_dir, os.path.basename(m.name)), "wb") as f:
                        f.write(tar.extractfile(m).read())
    # FLEURS columns: id, file_name, raw_transcription, transcription, phonemes, num_samples, gender
    with open(os.path.join(out, "test.tsv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["id", "file", "text", "gender", "seconds"])
        for r in rows:
            w.writerow([r[0], r[1], r[2], r[6], f"{int(r[5]) / 16000:.2f}"])
    print(f"FLEURS kam_ke test: {len(rows)} utterances, {len(set(r[0] for r in rows))} distinct sentences, "
          f"{sum(int(r[5]) for r in rows) / 16000 / 3600:.2f} h  sha256(text) {sha256_lines([r[1] + chr(9) + r[2] for r in rows])}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fleurs", action="store_true")
    args = ap.parse_args()
    fetch_flores()
    if args.fleurs:
        fetch_fleurs()
