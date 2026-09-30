// The voice contributor's anonymous profile and progress, kept in this
// browser's localStorage. Exposed as an external store for useSyncExternalStore.

export interface ContributorProfile {
  speakerId: string; // random UUID -- the only identifier we ever store
  dialect: string;
  gender: string;
  ageRange: string;
  consentVersion: string;
}

export interface ContributorState {
  profile: ContributorProfile | null;
  recorded: string[]; // prompt ids this browser has submitted
}

const KEY = "kikamba.contributor";
const EMPTY: ContributorState = { profile: null, recorded: [] };
const listeners = new Set<() => void>();
let cache: ContributorState | null = null;

function read(): ContributorState {
  try {
    return { ...EMPTY, ...JSON.parse(localStorage.getItem(KEY) ?? "{}") };
  } catch {
    return EMPTY;
  }
}

function write(state: ContributorState) {
  cache = state;
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    // Storage full or blocked -- keep the in-memory copy for this session.
  }
  listeners.forEach((l) => l());
}

export function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSnapshot(): ContributorState {
  cache ??= read();
  return cache;
}

export function getServerSnapshot(): ContributorState {
  return EMPTY;
}

/** Saves details and consent; keeps the existing contributor ID if there is one. */
export function saveProfile(details: Omit<ContributorProfile, "speakerId">) {
  const state = getSnapshot();
  write({ ...state, profile: { speakerId: state.profile?.speakerId ?? crypto.randomUUID(), ...details } });
}

export function markRecorded(promptId: string) {
  const state = getSnapshot();
  if (!state.recorded.includes(promptId)) write({ ...state, recorded: [...state.recorded, promptId] });
}

/** Back to the consent step (details can be changed); the ID and progress are kept. */
export function editProfile() {
  const state = getSnapshot();
  if (state.profile) write({ ...state, profile: { ...state.profile, consentVersion: "" } });
}
