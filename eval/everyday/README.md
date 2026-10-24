# Everyday test set (v1)

300 everyday Kikamba sentences for measuring the translator the way users experience it, instead of Wikipedia-style
FLORES text. Sampled (seed 1234) evenly across the 11 topics of the first part of Digital Divide Data's public Kamba
speech dataset ([gamamima/Kamba-ASR-Data-Subset-484H](https://huggingface.co/datasets/gamamima/Kamba-ASR-Data-Subset-484H),
CC-BY-4.0): greetings, hospitality, dining, gift giving, weddings, dating, dressing, etiquette, folklore, burials,
transport. 4-22 words, no written numbers.

| File | Contents |
|---|---|
| `sentences.tsv` | The 300 sentences with topic and DDD sentence id |
| `everyday_test_v1.xlsx` | The sheet for Kamba speakers: Kikamba, a machine draft in English (from `lawmaluki/nllb-200-1.3B-kamba-ft-ct2-int8`, to correct rather than translate from scratch), columns for the correct translation, naturalness, draft quality and a second check |

**Never train on these sentences.** They are excluded from every training set, including the planned back-translation
of the DDD sentences (match on the Kikamba text in `sentences.tsv`).

Process: two speakers per sheet (one translates/corrects, one checks). When sheets come back, the agreed translations
become the reference translations; the "draft quality" column already gives a first human rating of the current model.
