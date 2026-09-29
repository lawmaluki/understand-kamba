export const SAMPLE_SENTENCES = [
  "How are you? How has your day been today? We're here to help translate your words into beautiful Kikamba.",
  "Scared to have kids because I also want to give them the best.",
  "Good morning, my friend. Did you sleep well?",
  "Please bring some water from the river before evening.",
];

/** A random sample that differs from `current`, so the button always changes the text. */
export function pickSample(current: string): string {
  const others = SAMPLE_SENTENCES.filter((s) => s !== current);
  return others[Math.floor(Math.random() * others.length)];
}
