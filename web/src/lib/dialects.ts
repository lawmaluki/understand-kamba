export interface Dialect {
  id: string;
  label: string;
  short: string;
  description: string;
}

// Every dialect currently uses the same translation model (NLLB's single
// Kamba language code) and the same voice -- the choice labels the output
// but doesn't change it. Per-dialect models are future work.
export const DIALECTS: Dialect[] = [
  {
    id: "machakos",
    label: "Machakos Standard",
    short: "Machakos",
    description: "Conversational, standard Central Akamba orthography and tone.",
  },
  {
    id: "kitui",
    label: "Kitui",
    short: "Kitui",
    description: "Eastern Kamba vocabulary and pronunciation.",
  },
  {
    id: "makueni",
    label: "Makueni Conversational",
    short: "Makueni",
    description: "Everyday southern speech with a relaxed voice.",
  },
  {
    id: "elder",
    label: "Elder Storyteller",
    short: "Elder",
    description: "Formal register and a slower, narrative voice.",
  },
];
