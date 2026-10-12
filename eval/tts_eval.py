"""
Voice (text-to-speech) evaluation by ASR round trip.

100 sentences are drawn (seed 1234) from the FLEURS Kamba *test* split.
FLEURS splits by sentence, so a voice trained on FLEURS train/dev audio has
not seen these sentences. Each voice reads all 100; the app's Kamba ASR model
(FarmerlineML/w2v-bert-2.0_kamba) transcribes the audio, and we score
character error rate against the text (tier K1: diacritic-insensitive,
because the ASR writes no tildes). Real FLEURS recordings of the same
sentences go through the identical pipeline as a reference point.

Intelligibility to an ASR model is a proxy, not a listening test: it says
nothing about naturalness, and the ASR may favour FLEURS-like audio.

Voices:
  omnivoice-female / omnivoice-male  k2-fsa/OmniVoice cloning app/data/voices (GPU, float32)
  mms-swh / mms-kik                   facebook/mms-tts-swh / -kik (CPU)
  real                                the FLEURS recordings themselves

    python eval/tts_eval.py --generate mms         # project venv (CPU)
    python eval/tts_eval.py --generate omnivoice   # an env with omnivoice + CUDA torch
    python eval/tts_eval.py --score                # project venv: ASR + CER
"""
import argparse
import csv
import os
import random
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (DATA_DIR, OUTPUT_DIR, REPO_DIR, SEED, bootstrap_ci, corpus_rate, error_counts,  # noqa: E402
                    paired_test, protocol_block, sha256_lines, write_report)

N_SENTENCES = 100
FLEURS = os.path.join(DATA_DIR, "fleurs_kam")
AUDIO = os.path.join(DATA_DIR, "tts_audio")  # generated audio (large; not committed)
OUT = os.path.join(OUTPUT_DIR, "tts")
VOICES = ["real", "omnivoice-female", "omnivoice-male", "mms-swh", "mms-kik"]
BASELINE = "mms-swh"  # the app's previous voice (now its fallback)
os.makedirs(OUT, exist_ok=True)


def sentences():
    """The fixed sample: (index, text, a real FLEURS recording of it)."""
    path = os.path.join(OUT, "sentences.tsv")
    if not os.path.exists(path):
        with open(os.path.join(FLEURS, "test.tsv"), encoding="utf-8") as f:
            items = list(csv.DictReader(f, delimiter="\t"))
        by_text = {}
        for it in sorted(items, key=lambda r: (r["text"], r["file"])):
            by_text.setdefault(it["text"], it["file"])  # first recording of each sentence
        chosen = random.Random(SEED).sample(sorted(by_text), N_SENTENCES)
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["idx", "text", "real_file"])
            for i, t in enumerate(chosen):
                w.writerow([i, t, by_text[t]])
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def wav_path(voice: str, idx) -> str:
    if voice == "real":
        return None  # resolved per item from FLEURS
    return os.path.join(AUDIO, voice, f"{int(idx):03d}.wav")


def generate_mms():
    import soundfile as sf
    import torch
    from transformers import AutoTokenizer, VitsModel

    for code in ("swh", "kik"):
        voice = f"mms-{code}"
        os.makedirs(os.path.join(AUDIO, voice), exist_ok=True)
        tok = AutoTokenizer.from_pretrained(f"facebook/mms-tts-{code}")
        model = VitsModel.from_pretrained(f"facebook/mms-tts-{code}").eval()
        vocab = set(tok.get_vocab())
        for s in sentences():
            out = wav_path(voice, s["idx"])
            if os.path.exists(out):
                continue
            # Keep characters the voice knows (Kikuyu has ĩ/ũ); strip diacritics from the rest.
            chars = []
            for c in unicodedata.normalize("NFC", s["text"].lower().replace("’", "'")):
                if c in vocab or c == " ":
                    chars.append(c)
                else:
                    base = "".join(x for x in unicodedata.normalize("NFD", c) if not unicodedata.combining(x))
                    chars.append(base if base in vocab else " ")
            torch.manual_seed(SEED)
            with torch.inference_mode():
                wav = model(**tok(" ".join("".join(chars).split()), return_tensors="pt")).waveform[0].numpy()
            sf.write(out, wav, model.config.sampling_rate)
        print(f"[{voice}] done", flush=True)


def generate_omnivoice():
    import soundfile as sf
    import torch
    from omnivoice import OmniVoice

    model = OmniVoice.from_pretrained("k2-fsa/OmniVoice")
    voices_dir = os.path.join(REPO_DIR, "app", "data", "voices")
    prompts = {}
    for g in ("female", "male"):
        samples, sr = sf.read(os.path.join(voices_dir, f"kamba_{g}.wav"), dtype="float32")
        ref = open(os.path.join(voices_dir, f"kamba_{g}.txt"), encoding="utf-8").read().strip()
        prompts[g] = model.create_voice_clone_prompt((torch.from_numpy(samples).unsqueeze(0), sr), ref)
    model = model.to("cuda")  # float32, as deployed (float16 casting produced silence)
    for g, prompt in prompts.items():
        voice = f"omnivoice-{g}"
        os.makedirs(os.path.join(AUDIO, voice), exist_ok=True)
        for s in sentences():
            out = wav_path(voice, s["idx"])
            if os.path.exists(out):
                continue
            torch.manual_seed(SEED)
            audio = model.generate(text=s["text"], language="kam", voice_clone_prompt=prompt)
            sf.write(out, audio[0], 24000)
        print(f"[{voice}] done", flush=True)


def score():
    sys.path.insert(0, REPO_DIR)
    from app import asr, audio

    items = sentences()
    refs = [s["text"] for s in items]
    hyps_path = os.path.join(OUT, "asr_transcripts.tsv")
    cached = {}
    if os.path.exists(hyps_path):
        cached = {(r["voice"], r["idx"]): r["hypothesis"] for r in csv.DictReader(open(hyps_path, encoding="utf-8"), delimiter="\t")}
    tmp = os.path.join(AUDIO, "_16k.wav")
    with open(hyps_path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        if not cached:
            w.writerow(["voice", "idx", "hypothesis"])
        for voice in VOICES:
            for s in items:
                if (voice, s["idx"]) in cached:
                    continue
                src = os.path.join(FLEURS, "test", s["real_file"]) if voice == "real" else wav_path(voice, s["idx"])
                if not os.path.exists(src):
                    break  # this voice hasn't been generated yet
                audio.to_wav_16k_mono(src, tmp)  # resample everything to the ASR's 16 kHz the same way
                cached[(voice, s["idx"])] = asr.transcribe_wav_file(tmp)
                w.writerow([voice, s["idx"], cached[(voice, s["idx"])]])
                f.flush()
    if os.path.exists(tmp):
        os.remove(tmp)

    report = {"test_set": f"{N_SENTENCES} sentences sampled (seed {SEED}) from FLEURS kam_ke test",
              "sentences_sha256": sha256_lines(refs), "asr_model": "FarmerlineML/w2v-bert-2.0_kamba",
              "protocol": protocol_block(primary_metric="CER of the ASR transcript vs the input text (tier K1)",
                                         secondary_metric="CER at tier K0, WER at K1"),
              "voices": {}, "paired_vs_" + BASELINE: {}}
    counts = {}
    for voice in VOICES:
        if not all((voice, s["idx"]) in cached for s in items):
            print(f"skip {voice}: not complete")
            continue
        hyps = [cached[(voice, s["idx"])] for s in items]
        c1, c0 = error_counts(refs, hyps, "K1"), error_counts(refs, hyps, "K0")
        counts[voice] = c1
        report["voices"][voice] = {
            "cer_k1": round(corpus_rate(c1[:, 0], c1[:, 1]), 4), "cer_k1_ci95": [round(x, 4) for x in bootstrap_ci(c1[:, 0], c1[:, 1])],
            "wer_k1": round(corpus_rate(c1[:, 2], c1[:, 3]), 4), "wer_k1_ci95": [round(x, 4) for x in bootstrap_ci(c1[:, 2], c1[:, 3], seed=1235)],
            "cer_k0": round(corpus_rate(c0[:, 0], c0[:, 1]), 4),
            "empty_transcripts": int(sum(1 for h in hyps if not h.strip())),
        }
    for voice, c in counts.items():
        if voice != BASELINE and BASELINE in counts:
            b = counts[BASELINE]
            report["paired_vs_" + BASELINE][voice] = paired_test(c[:, 0], c[:, 1], b[:, 0], b[:, 1])
    path = write_report("tts_asr_roundtrip", report)
    for v, r in report["voices"].items():
        p = report["paired_vs_" + BASELINE].get(v, {})
        print(f"{v:17} CER(K1) {r['cer_k1']:.4f} {r['cer_k1_ci95']}  WER(K1) {r['wer_k1']:.4f}  CER(K0) {r['cer_k0']:.4f}"
              f"  empty={r['empty_transcripts']}  {'p=' + format(p['p_value_one_sided'], '.4f') if p else ''}")
    print("report:", path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", choices=["mms", "omnivoice"])
    ap.add_argument("--score", action="store_true")
    args = ap.parse_args()
    if args.generate == "mms":
        generate_mms()
    elif args.generate == "omnivoice":
        generate_omnivoice()
    if args.score:
        score()
