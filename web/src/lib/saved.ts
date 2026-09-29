// Saved translations, kept in this browser's localStorage. Exposed as a tiny
// external store so components can read it with useSyncExternalStore.
import type { Direction } from "./api";

export interface SavedTranslation {
  id: string;
  direction: Direction;
  source: string;
  translation: string;
  savedAt: number;
}

const KEY = "kikamba.saved";
const EMPTY: SavedTranslation[] = [];
const listeners = new Set<() => void>();
let cache: SavedTranslation[] | null = null;

function read(): SavedTranslation[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "[]");
  } catch {
    return EMPTY;
  }
}

function write(items: SavedTranslation[]) {
  cache = items;
  try {
    localStorage.setItem(KEY, JSON.stringify(items));
  } catch {
    // Storage full or blocked -- keep the in-memory copy for this session.
  }
  listeners.forEach((l) => l());
}

export function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSnapshot(): SavedTranslation[] {
  cache ??= read();
  return cache;
}

export function getServerSnapshot(): SavedTranslation[] {
  return EMPTY;
}

/** Returns false if this exact translation is already saved. */
export function save(item: Omit<SavedTranslation, "id" | "savedAt">): boolean {
  const items = getSnapshot();
  if (items.some((s) => s.source === item.source && s.translation === item.translation)) return false;
  write([{ ...item, id: crypto.randomUUID(), savedAt: Date.now() }, ...items]);
  return true;
}

export function remove(id: string) {
  write(getSnapshot().filter((s) => s.id !== id));
}
