# Training

Improve the translator using only existing public data, on a free Kaggle or Colab GPU.

| File | What it does |
|---|---|
| `build_parallel.py` | Builds the clean, human-translated pairs below |
| `filter_opus.py` | Picks the usable part of the 1.6M machine-mined OPUS pairs → `data/opus_filtered.tsv.gz` (14,818 pairs) |
| `finetune_nllb.py` | Fine-tunes NLLB with LoRA and compares it with the original model |
| `finetune_kaggle.ipynb` | Notebook that runs all of it on a free GPU |
| `voice_kaggle.ipynb` | Trains a Kamba voice from a consenting contributor's recordings (MMS Swahili voice fine-tuned on her clips); runs on CPU once trained |
| `review_corrections.py` | Exports corrections users sent from the app for review, and imports the approved ones into `data/community/` |

## How to run the fine-tuning

1. Open [kaggle.com](https://www.kaggle.com) → *Create* → *Notebook* → *File* → *Import notebook* → upload `finetune_kaggle.ipynb` (or open it in Google Colab).
2. Turn on the GPU (Kaggle: *Accelerator: GPU T4 x2* and *Internet: On*; Colab: *Runtime → T4 GPU*).
3. *Run all*. It takes about 1.5–2 hours and prints a table: original vs fine-tuned model, on FLORES devtest (formal text) and on 10 held-out children's stories (everyday text), in both directions.
4. Only if the fine-tuned model is better on both test sets, run the last cell to upload it (privately) to Hugging Face. It can then be put on the Space by setting `NLLB_GPU_MODEL_ID` to the new model.

Check: `python training/finetune_nllb.py --model facebook/nllb-200-distilled-600M --smoke` runs a tiny version on CPU.

## Filtered OPUS pairs

`filter_opus.py` keeps pairs with a good mining score whose Kikamba side really is Kikamba (written with ĩ/ũ, no Hindi/English), removes religious text and duplicates, and anything overlapping FLORES. 14,818 of 1.63M pairs survive. Some are still loosely aligned, so `finetune_nllb.py` drops the worst 40% again using the model's own translation scores in both directions (dual conditional cross-entropy).

## Clean pairs

Only human-translated pairs are kept here.

| File | Pairs | Contents |
|---|---|---|
| `data/kam_eng.tsv` | 1,415 | Kikamba ⇄ English |
| `data/kam_swh.tsv` | 1,352 | Kikamba ⇄ Swahili |

Columns: `kam`, `eng` (or `swh`), `source`, `license`, `doc` (the story a sentence comes from). Rebuild with `python training/build_parallel.py`.

## Sources

| Source | kam–eng | kam–swh | What it is | Licence |
|---|---|---|---|---|
| GlotStoryBook | 410 | 355 | Children's stories, translated by people (everyday language) | CC-BY-4.0 / CC-BY-NC-4.0 per story |
| FLORES-200 **dev** | 995 | 997 | Professional translations of Wikipedia-style sentences | CC-BY-SA-4.0 |
| Tatoeba | 10 | — | Short conversational sentences | CC-BY-2.0-FR |
| Your own (`data/community/*.tsv`) | — | — | Pairs translated by Kamba speakers | Project's own |

All are taken from [kithyadan/kikamba-corpus](https://github.com/kithyadan/kikamba-corpus) at a pinned commit. 56 pairs that were empty, truncated ("...") or badly misaligned are dropped.

**FLORES devtest is never included**: it is the test set the paper and `eval/` score against. Training on it would make every score meaningless.

## Left out on purpose

| Source | Why |
|---|---|
| OPUS NLLB (1.6M pairs) | Machine-mined from the web, often misaligned, mostly religious. NLLB was already trained on it. |
| FineTranslations (1,435) | The English side is machine translation of JW web pages |
| Bloom (134) | Religious only, and CC-BY-NC-ND (no derivatives) |
| KnoxDevelopers (31k) | Bible verses; did not improve scores in our tests |
| JW300 | Religious; withdrawn from OPUS over copyright |

## Adding your own pairs

This is how the dataset will grow. Put a TSV file (UTF-8, tab-separated, with a header row) in `data/community/`:

```
kam	eng
Wĩ mũseo?	Are you well?
```

Use `kam	swh` as the header for Swahili. Then rerun `python training/build_parallel.py`; the pairs are merged and de-duplicated.

Guidelines for translators:

- Everyday sentences people actually say: greetings, family, market, farming, health, school, church, directions.
- One sentence per row; natural English, not word-for-word.
- Write the Kikamba the way it is normally written; note the dialect in the file name (for example `kitui-2026-10.tsv`).
- Have a second speaker check each file.
- Keep 300 pairs aside in a file named `test-*.tsv`. Do not train on these; use them to measure whether a fine-tuned model is actually better.

## Licences

The training data mixes licences. CC-BY-NC stories mean a model trained on them should stay non-commercial, which the deployed NLLB model already is. CC-BY-SA (FLORES) requires attribution and share-alike for the data itself. Credit the GlotStoryBook / African Storybook authors and translators when publishing a model.

## Training a contributor's voice

`voice_kaggle.ipynb` fine-tunes Meta's MMS Swahili voice on recordings of one consenting speaker (private dataset
`lawmaluki/kamba-voice-tts-contributor`, built from her `/contribute` recordings). The result is a small model that
runs on CPU, so it never depends on the GPU allowance. Run it on Kaggle like the translation notebook; also add your
Hugging Face token as a Kaggle secret named `HF_TOKEN` (Add-ons → Secrets). It ends with a listening comparison and an
intelligibility test against the original Swahili voice.

With her current ~3 minutes this is an experiment; 80–150 recordings (15–20 minutes) are recommended. The model cannot
pronounce ĩ/ũ differently from i/u, because the Swahili voice it starts from has no such letters.
