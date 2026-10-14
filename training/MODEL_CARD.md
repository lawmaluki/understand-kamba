---
license: cc-by-nc-4.0
language:
- kam
- en
base_model: facebook/nllb-200-distilled-1.3B
pipeline_tag: translation
library_name: transformers
tags:
- nllb
- kikamba
- kamba
- low-resource
- african-languages
datasets:
- openlanguagedata/flores_plus
metrics:
- chrf
---

# NLLB-200 1.3B fine-tuned for Kikamba ⇄ English

[`facebook/nllb-200-distilled-1.3B`](https://huggingface.co/facebook/nllb-200-distilled-1.3B), fine-tuned with LoRA (merged into the weights) to translate between **Kikamba** (Kamba, `kam_Latn`, Kenya) and **English** (`eng_Latn`). It powers the [Understand Kamba](https://understand-kamba.vercel.app) translator.

**It still makes mistakes.** It is clearly better than the base model, but key nouns are often wrong (for example *"Ilinda yii ni yaasa"*, "this dress is long", comes out as "this line is long"). Do not rely on it for medical, legal or other important text without a fluent speaker checking.

## Results

chrF++ (higher is better), on test sentences the model never saw. Both models are decoded the same way: beam 5, `no_repeat_ngram_size=4`, output capped at 2 × input length + 16 tokens.

| Test set | Direction | Base 1.3B | This model | Change |
|---|---|---|---|---|
| Children's stories, 91 sentences from 10 held-out stories (everyday language) | Kikamba → English | 25.5 | **37.1** | +11.6 |
| | English → Kikamba | 26.8 | **29.2** | +2.5 |
| FLORES-200 devtest, 1,012 sentences (Wikipedia-style) | Kikamba → English | 34.1 | **44.3** | +10.2 |
| | English → Kikamba | 27.7 | **33.4** | +5.7 |

- **Leakage check:** only 2 of the 91 story test sentences and 2 of the 1,012 FLORES test sentences have a near-duplicate (≥ 80% similar) in the training data.
- **Caveats:** the model was trained on other stories from the same collection and on FLORES *dev*, which are similar in style to the test sets, so gains on people's own everyday sentences are probably smaller. Only 35% of FLORES Kikamba references use the letters ĩ/ũ, which the model always writes, so English → Kikamba scores are partly a spelling penalty. All scores are automatic; no human evaluation has been done.
- A second training run with identical settings scored within 0.5 chrF++ of these numbers.

## Training data

Only existing public data, about 10,200 sentence pairs, used in both directions:

| Source | Pairs | Notes | Licence |
|---|---|---|---|
| [GlotStoryBook](https://github.com/global-asp/asp-source) (African Storybook) children's stories | 319 (after holding out 10 stories) | Human translations, everyday language; translated by Stephen Musyoka and others | CC-BY-4.0 / CC-BY-NC-4.0 |
| [FLORES-200](https://github.com/facebookresearch/flores) **dev** | 995 | Professional translations; devtest is never used for training | CC-BY-SA-4.0 |
| Tatoeba | 10 | Short conversational sentences | CC-BY-2.0-FR |
| [OPUS NLLB](https://opus.nlpl.eu/NLLB/corpus/version/NLLB) mined pairs, filtered | 8,890 of 1.63M | Kept only real Kikamba (written with ĩ/ũ), non-religious, de-duplicated, no FLORES overlap, then the 60% best-aligned by the base model's own dual cross-entropy scores | ODC-By-1.0 |

The human-translated pairs were repeated 3 times. Pairs were taken from [kithyadan/kikamba-corpus](https://github.com/kithyadan/kikamba-corpus).

## Training setup

LoRA r = 16, α = 32, dropout 0.05 on `q_proj, k_proj, v_proj, out_proj, fc1, fc2` (23.6M trainable parameters), learning rate 2e-4 with cosine decay and 5% warm-up, effective batch 32, 2 epochs (1,608 steps), fp16 mixed precision on one Kaggle T4, about 1.5 hours. The LoRA weights are merged into this checkpoint. Code: [`training/`](https://github.com/lawmaluki/understand-kamba/tree/main/training) in the project repository.

## Usage

```python
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

repo = "lawmaluki/nllb-200-1.3B-kamba-ft"
tok = AutoTokenizer.from_pretrained(repo)
model = AutoModelForSeq2SeqLM.from_pretrained(repo)

tok.src_lang = "kam_Latn"                     # "eng_Latn" for English -> Kikamba
inputs = tok("Tene tene vyũ, eĩtu atatũ nĩmaendie kuna ngũ.", return_tensors="pt")
out = model.generate(**inputs, forced_bos_token_id=tok.convert_tokens_to_ids("eng_Latn"),
                     num_beams=5, no_repeat_ngram_size=4, max_new_tokens=128)
print(tok.decode(out[0], skip_special_tokens=True))
```

Translate one sentence at a time; NLLB drops or invents clauses in long paragraphs.

## Limitations

- Trained on little everyday Kikamba. Common words in conversation, farming, markets and family life are often mistranslated.
- No dialect handling: Machakos, Kitui and Makueni varieties are not distinguished.
- Inherits the biases of its sources: the mined web data was heavily religious before filtering.
- Users of the Understand Kamba app can submit corrections; reviewed corrections will be used to train later versions.

## Licence

CC-BY-NC-4.0, the licence of the NLLB-200 base model: **non-commercial use only**. Please credit the African Storybook / GlotStoryBook authors and translators and the FLORES-200 creators when you use this model.

## Citation

Maluki, L. (2026). *Understand Kamba: An Open English–Kikamba Translation, Speech Recognition and Voice System on Free Infrastructure.* https://github.com/lawmaluki/understand-kamba
