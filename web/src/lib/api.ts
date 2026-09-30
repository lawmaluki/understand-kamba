const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Keep in sync with MAX_TRANSLATE_CHARS in app/config.py.
export const MAX_TRANSLATE_CHARS = 500;
// Keep in sync with MAX_AUDIO_SECONDS in app/config.py (longer audio is trimmed).
export const MAX_RECORDING_SECONDS = 60;

export type Direction = "en_to_kam" | "kam_to_en";

export interface Stats {
  translations: number;
  ratings_up: number;
  ratings_down: number;
}

async function errorMessage(resp: Response): Promise<string> {
  try {
    const { detail } = await resp.json();
    if (typeof detail === "string") return detail;
    // FastAPI validation errors: [{ msg: "..." }, ...]
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  } catch {
    // Not JSON -- fall through to the generic message.
  }
  return `Request failed (HTTP ${resp.status}).`;
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE_URL}${path}`, init);
  } catch {
    throw new Error(`Couldn't reach the translation server at ${API_BASE_URL}. Is it running?`);
  }
  if (!resp.ok) throw new Error(await errorMessage(resp));
  return resp;
}

function postJson(path: string, body: unknown): Promise<Response> {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function translateText(text: string, direction: Direction): Promise<string> {
  const data = await (await postJson("/translate", { text, direction })).json();
  return (direction === "en_to_kam" ? data.translation_kam : data.translation_en) ?? "";
}

/** Kikamba speech -> Kikamba text. */
export async function transcribeAudio(audio: Blob, filename: string): Promise<string> {
  const form = new FormData();
  form.append("file", audio, filename);
  const data = await (await request("/transcribe?translate=false", { method: "POST", body: form })).json();
  return data.transcript ?? "";
}

/** Kikamba text -> WAV audio. */
export async function synthesizeSpeech(text: string): Promise<Blob> {
  return (await postJson("/synthesize", { text })).blob();
}

export async function getStats(): Promise<Stats> {
  return (await request("/stats")).json();
}

export interface VoicePrompt {
  id: string;
  text: string;
}

export interface VoicePrompts {
  prompts: VoicePrompt[];
  consent_version: string;
  max_seconds: number;
}

/** Kikamba sentences for voice contributors to read aloud. */
export async function getVoicePrompts(): Promise<VoicePrompts> {
  return (await request("/voice/prompts")).json();
}

export interface SpeakerDetails {
  speakerId: string;
  dialect: string;
  gender: string;
  ageRange: string;
}

/** Upload one contributed recording of a prompt sentence. */
export async function submitVoiceRecording(
  audio: Blob,
  filename: string,
  promptId: string,
  speaker: SpeakerDetails
): Promise<void> {
  const form = new FormData();
  form.append("file", audio, filename);
  form.append("prompt_id", promptId);
  form.append("speaker_id", speaker.speakerId);
  form.append("dialect", speaker.dialect);
  form.append("gender", speaker.gender);
  form.append("age_range", speaker.ageRange);
  form.append("consent", "true");
  await request("/voice/recordings", { method: "POST", body: form });
}

export async function sendFeedback(feedback: {
  rating: "up" | "down";
  direction: Direction;
  text: string;
  translation: string;
}): Promise<Stats> {
  return (await postJson("/feedback", feedback)).json();
}
