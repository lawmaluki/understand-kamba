# Understand Kamba — Contributor and Data Guide

This guide is for everyone who helps improve Understand Kamba: Kikamba speakers who record their voice or correct translations, developers who send code, and the maintainer who looks after the collected data. It explains what we collect, why, how it is protected, and how to handle requests.

---

## 1. Ways to contribute

| You are… | You can… | Section |
|---|---|---|
| A fluent Kikamba speaker, 18+ | Record sentences for a real Kamba voice | 2 |
| Any Kikamba speaker | Rate translations; suggest better ones | 3 |
| A developer | Fix bugs, add features, improve evaluation | 4 |
| Someone with a Kikamba text or audio collection | Offer data, with its licence | 5 |

---

## 2. Recording your voice

### Why

The app's Kamba voice is currently cloned from two speakers in Google's FLEURS dataset, who recorded for research but never agreed to be an app's voice. We want to replace them with speakers who choose to, and to train voices and speech recognition that cover Machakos, Kitui, Makueni and other varieties, women and men, young and old.

### How

1. Open https://understand-kamba.vercel.app/contribute
2. Read **How your recordings are used**, choose your dialect, and optionally your gender and age range.
3. Confirm you are 18 or older, speak Kikamba fluently, and agree to the use described.
4. For each sentence: record, listen back, then **Submit**, **Re-record** or **Skip**.

Good recordings:

- A quiet room, with no music, TV or wind.
- The phone 15–30 cm from your mouth.
- Read the sentence exactly as written, at a natural pace. If a word is spelt in a way you would not say, **Skip** the sentence.
- Each recording must be 1–20 seconds long and not silent; the server rejects others with a message.

### What is stored with each recording

| Field | Example | Notes |
|---|---|---|
| Audio | 16 kHz mono WAV | Converted on the server |
| `text`, `prompt_id` | the sentence read | From `app/data/kikamba_prompts.tsv` |
| `speaker_id` | random UUID | Generated in your browser; not linked to your name |
| `dialect` | `machakos` / `kitui` / `makueni` / `other` | Required |
| `gender` | `female` / `male` / `other` / empty | Optional |
| `age_range` | `18-29` / `30-44` / `45-59` / `60+` / empty | Optional |
| `duration_seconds`, `sample_rate` | 4.2, 16000 | |
| `consent_version` | `2026-09-30` | The wording you agreed to |
| `recorded_at` | UTC timestamp | |

We do **not** store your name, phone number, email, location or IP address with recordings. (The IP address is held in server memory for up to an hour, only to limit how many uploads one connection can send.)

### Where it goes

Recordings are saved on the server and pushed every few minutes to the **private** Hugging Face dataset `lawmaluki/kamba-voice-recordings`, which only the project maintainer can open. They are used to build and test Kamba speech technology. Models trained on them may be published openly; the recordings themselves are not published without a separate decision that respects the consent given.

### Deleting your recordings

Your Contributor ID is shown at the bottom of the recording page. **Write it down** — it lives only in your browser, and without it we cannot find your recordings.

To ask for deletion, tap **Ask to delete my recordings**. This opens a GitHub issue with your ID filled in. Note that GitHub issues are public and need a GitHub account; your ID is a random number, so publishing it does not reveal who you are. If you prefer, contact the maintainer privately instead.

---

## 3. Improving translations

- **Correct it in the app.** Give a translation a thumbs down and a box opens: *Help fix this translation*. It shows up to three other likely translations from the model; tap one, edit it if needed, or type the correct translation yourself, then **Send correction**. The selected dialect is saved with it.
- Corrections are saved without your name to a private dataset (`lawmaluki/kamba-translation-corrections`). After a Kamba speaker approves them they become training pairs for the next fine-tuning run, and may be published with the project's open training data. Don't type personal details.
- You can also open an issue at https://github.com/lawmaluki/understand-kamba/issues with the source text, the app's output and your correction.

The most valuable thing for translation quality is a set of **everyday sentences with careful Kikamba translations** (see section 5). A few thousand such pairs could improve English → Kikamba substantially; the public data available today is mostly Bible text.

---

## 4. Contributing code

1. Fork the repository and create a branch.
2. Set up the backend and web app as described in DOCUMENTATION.md, section 4.
3. Keep changes focused. Match the style of the code around you.
4. Run `npm run lint` and `npm run build` in `web/` for front-end changes.
5. For anything that could change translation, speech recognition or voice output, run the relevant evaluation in `eval/` (section 6) and report the numbers before and after in your pull request.
6. Never commit `.env`, `web/.env.local`, tokens or recordings.

---

## 5. Offering data

We welcome Kikamba text, parallel translations and recordings, but only with a clear right to use them. Please tell us:

- where the data came from and who created it;
- its licence, or written permission from the owner;
- for recordings of people: that the speakers consented to this kind of use;
- the domain (conversation, news, religious, education…) and dialect.

We do not accept data scraped from sources whose terms forbid it, or recordings of people who did not agree to be recorded.

---

## 6. Evaluation data hygiene

The scores in the research paper come from public test sets, which must stay unseen by any model we train:

| Test set | Used for | Rule |
|---|---|---|
| FLORES-200 dev and devtest | Translation scores | Never train a translation model on these sentences |
| FLEURS `kam_ke` test | Speech recognition and voice scores | Never train speech models on its audio or sentences |

The reading prompts on the contribute page **are FLORES sentences** (`app/data/kikamba_prompts.tsv`, CC-BY-SA 4.0). So:

- contributed recordings must **not** be used to train a model that is then scored on FLORES or FLEURS sentences — or those sentences must be removed from training first;
- a future evaluation set built from contributions must be split **by speaker**, so the same person is never in both training and test data.

The test-set fingerprints (SHA-256) are listed in the paper's appendix and in every `eval/results/*.json`. If a fingerprint changes, the scores are not comparable.

---

## 7. For the maintainer: handling the data

### Legal basis

Voice recordings are personal data, and gender and age range are personal details, under **Kenya's Data Protection Act, 2019**. The project relies on **consent**. Consent must be specific, informed and withdrawable, which is why the consent wording is versioned (`CONSENT_VERSION` in `app/voice.py`) and stored with every recording.

- If you change what the recordings are used for, update the wording on the consent screen **and** bump `CONSENT_VERSION`. Existing recordings stay under the version their speaker agreed to.
- Keep the dataset **private**. Before making any part public, check that every included recording's consent version allows it.
- If the project grows, consider registering with the Office of the Data Protection Commissioner (ODPC) and writing a short data-protection impact assessment.

### Deletion requests

Respond promptly; aim for within a week.

1. Get the full Contributor ID (the issue body has it; the page shows only the first 8 characters).
2. Clone the private dataset `lawmaluki/kamba-voice-recordings`.
3. In every `data/<session>/` folder, delete `audio/<speaker_id>/` and remove that speaker's lines from `metadata.jsonl`.
4. Commit and push. Old versions remain in the repository history, so either squash the history (`huggingface_hub.HfApi().super_squash_history`) or recreate the repository.
5. If a model was already trained on the recordings, note this in the reply and exclude the speaker from future training.
6. Reply on the issue (without restating any personal details) and close it.

### Reviewing translation corrections

Users can type anything, so corrections are never trained on unreviewed. Every few hundred corrections:

1. `python training/review_corrections.py export` (needs `HF_TOKEN`) writes a sheet to `training/data/review/` (never committed: it may contain personal details).
2. Open it in Excel or Google Sheets. For each row put `y` in **approve** if the correction is right and contains nothing personal, `n` otherwise. You may fix the correction text. Save as tab-separated text.
3. `python training/review_corrections.py import <sheet>` writes the approved pairs to `training/data/community/`.
4. `python training/build_parallel.py`, commit, push, and rerun the fine-tuning notebook. Deploy the new model only if it beats the current one.

Reject rows with names, phone numbers, addresses or anything else that identifies a person, and joke or abusive entries.

### Replacing the reference voices

When a contributor explicitly agrees to be **the app's voice** (a separate, stronger consent than contributing recordings):

1. Pick a clean 8–12 second recording of them.
2. Replace `app/data/voices/kamba_female.wav` or `kamba_male.wav`, and put its exact transcript in the matching `.txt`.
3. Update `app/data/voices/README.md` with the new credit.
4. Redeploy the Space (`python scripts/deploy_space.py`) and listen to a few sentences.

### Licences in the project

| Material | Licence |
|---|---|
| Project code | See the repository licence |
| NLLB-200 weights | CC-BY-NC 4.0 (non-commercial) |
| OmniVoice weights | CC-BY-NC (non-commercial); code Apache-2.0 |
| FarmerlineML Kamba ASR | See its model card |
| FLORES-200 sentences (and the reading prompts) | CC-BY-SA 4.0 |
| FLEURS audio (current reference voices) | CC-BY 4.0 |
| Contributed recordings | Private; use limited by the consent version |
| Translation corrections | Private until reviewed; approved pairs published in `training/data/community/` |

Because of the NLLB and OmniVoice licences, the deployed service is non-commercial.
