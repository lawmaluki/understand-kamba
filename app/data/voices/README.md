# Reference voices for OmniVoice

OmniVoice (see space/server.py) reads Kikamba aloud by cloning one of these
two 8-second recordings of native Kamba speakers:

| File | Speaker | Transcript |
|---|---|---|
| kamba_female.wav | Woman | kamba_female.txt |
| kamba_male.wav | Man | kamba_male.txt |

Source: Google FLEURS, Kamba (kam_ke) dev split,
https://huggingface.co/datasets/google/fleurs — licensed CC-BY-4.0.
Credit: Conneau et al., "FLEURS: Few-shot Learning Evaluation of Universal
Representations of Speech" (2022).

The FLEURS speakers recorded for research and evaluation. Before wider
public use, consider replacing these with recordings from Kamba speakers who
have agreed to be the app's voice (for example via the /contribute page):
replace the .wav (8-12 s, one speaker, quiet room) and its exact .txt
transcript, then redeploy.
