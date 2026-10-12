# Evaluation

Scripts that produce every number in the paper. The protocol (bootstrap settings, normalisers, edit distance) is pinned in `common.py`; every report in `results/` records the protocol, library versions and the exact command.

| Component | Test set | Metric | Script |
|---|---|---|---|
| Translation | FLORES-200 devtest, 1,012 sentences, both directions | chrF++ (primary), BLEU; tiers T0 raw / T1 tilde-folded for English → Kikamba | `mt_translate.py`, `mt_score.py` |
| Speech recognition | FLEURS `kam_ke` test, 827 utterances (3.73 h) | CER (primary), WER; tiers K0 / K1 (diacritics dropped); by gender | `asr_eval.py` |
| Voice | 100 FLEURS-test sentences (seed 1234) | CER (K1) of the app's ASR on the synthesised audio, against real recordings | `tts_eval.py` |

All intervals are 95% bootstrap intervals with 2,000 resamples, seed 1234. Paired tests compare against the original baselines (NLLB-600M; MMS Swahili voice; Farmerline vs MMS for ASR).

## Running

From the repository root, with the project venv (`pip install sacrebleu` in addition to `requirements.txt`):

```
python eval/fetch_data.py --fleurs                     # test sets -> eval/data/ (not committed)

python eval/mt_translate.py --system nllb-600m --device cuda
python eval/mt_translate.py --system nllb-1.3b --device cuda
python eval/mt_translate.py --system nllb-3.3b         # through the live Space API
python eval/mt_score.py

python eval/asr_eval.py --system farmerline --device cuda
python eval/asr_eval.py --system mms --device cuda
python eval/asr_eval.py --score

python eval/tts_eval.py --generate mms
python eval/tts_eval.py --generate omnivoice           # needs omnivoice + CUDA torch
python eval/tts_eval.py --score

python paper/make_numbers.py                           # results -> paper/numbers.tex
```

Every generation step is resumable: re-running continues where it stopped. `--device cpu` works everywhere but is slow.

The 3.3B run calls the deployed API and **stops** if any answer comes from the CPU fallback model (the response names its model), so outputs are never mixed. If the Space's GPU quota runs out, re-run later to resume.

## Layout

```
common.py        protocol: normalisers, Levenshtein, bootstrap, paired test, report writer
fetch_data.py    downloads FLORES-200 and FLEURS kam_ke test, prints their SHA-256
outputs/mt/      <system>.<direction>.txt, one line per source line
outputs/asr/     <system>.tsv transcripts
outputs/tts/     sentences.tsv (the fixed sample), asr_transcripts.tsv
results/         mt_flores_devtest.json, asr_fleurs_test.json, tts_asr_roundtrip.json
data/            downloaded test sets and generated audio (gitignored)
```

## Test-set fingerprints (SHA-256 of the lines)

| File | SHA-256 |
|---|---|
| FLORES `kam_Latn.devtest` | `4ca915187b3fb35c61ad2b45eddd5b8ac85f3d6723ff477c110ff06f55fba1dc` |
| FLORES `eng_Latn.devtest` | `612e9fbe87997617c0fa8fa8929654a4f49b728d96738112c2b86ef6a1d78d88` |
| FLORES `kam_Latn.dev` | `a500dfe801ba81c057465dd1b1cbb93874506d3defcf984d6765a0b44d77fc03` |
| FLORES `eng_Latn.dev` | `51a25f527fd81f428b6933d85a2f5e5544af92aa82042c7fbf0c4120327fba0a` |
| FLEURS `kam_ke` test (`file\ttext` lines) | `477beedb5f82d1078a4acfe9558d5d9b29066ebc8399ab76ccb3c780a191fefb` |
| TTS 100-sentence sample | `96f0db09f4009c7c2374f84cf1799be73e099cae001910fa61948cb01ee5ab4f` |

## Caveats

- No human evaluation: chrF++ against one reference, and ASR as a proxy for voice intelligibility.
- Only 35% of FLORES Kikamba references use ĩ/ũ, so English → Kikamba scores are reported raw (T0) and tilde-folded (T1); never quote T1 alone.
- The training data of the Farmerline ASR model and OmniVoice may include FLEURS audio; their FLEURS scores may be optimistic.
