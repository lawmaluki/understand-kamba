"use client";

import { useSyncExternalStore } from "react";
import { Languages, Loader2, Shuffle, X } from "lucide-react";
import { MAX_TRANSLATE_CHARS, type Direction } from "@/lib/api";
import { pickSample } from "@/lib/samples";
import AudioPlayer from "./AudioPlayer";
import VoiceInput from "./VoiceInput";

const noopSubscribe = () => () => {};

interface ContentAreaProps {
  direction: Direction;
  dialectShort: string;
  sourceText: string;
  onSourceTextChange: (value: string) => void;
  translatedText: string;
  isTranslating: boolean;
  error: string | null;
  onTranslate: (text?: string) => void;
  onNotice: (message: string) => void;
}

export default function ContentArea({
  direction,
  dialectShort,
  sourceText,
  onSourceTextChange,
  translatedText,
  isTranslating,
  error,
  onTranslate,
  onNotice,
}: ContentAreaProps) {
  const fromEnglish = direction === "en_to_kam";
  const charCount = sourceText.length;
  const overLimit = charCount > MAX_TRANSLATE_CHARS;
  const canTranslate = !isTranslating && !!sourceText.trim() && !overLimit;
  const isMac = useSyncExternalStore(
    noopSubscribe,
    () => /Mac|iPhone|iPad/.test(navigator.platform),
    () => false
  );

  const kikambaBadge = (
    <span className="rounded-md bg-butter-200 px-1.5 py-0.5 text-[11px] font-medium text-butter-900">
      {dialectShort}
    </span>
  );

  return (
    <div className="grid border-b border-neutral-200 md:grid-cols-2">
      {/* Source */}
      <div className="flex min-h-[15rem] flex-col border-b border-neutral-200 p-4 sm:p-5 md:border-b-0 md:border-r">
        <div className="mb-3 flex h-7 items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <label
              htmlFor="source-text"
              className="text-xs font-semibold uppercase tracking-[0.12em] text-neutral-500"
            >
              {fromEnglish ? "English" : "Kikamba"}
            </label>
            {!fromEnglish && kikambaBadge}
          </div>
          <div className="flex items-center gap-1">
            {fromEnglish ? (
              <button
                type="button"
                onClick={() => onSourceTextChange(pickSample(sourceText))}
                className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-butter-700 transition hover:bg-butter-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500"
              >
                <Shuffle className="h-3.5 w-3.5" aria-hidden />
                Sample
              </button>
            ) : (
              <VoiceInput
                onTranscript={(text) => {
                  onSourceTextChange(text);
                  onTranslate(text);
                }}
                onError={onNotice}
              />
            )}
            <button
              type="button"
              aria-label="Clear text"
              onClick={() => onSourceTextChange("")}
              disabled={!sourceText}
              className="inline-flex h-7 w-7 items-center justify-center rounded-md text-neutral-400 transition hover:bg-neutral-100 hover:text-neutral-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 disabled:opacity-40"
            >
              <X className="h-3.5 w-3.5" aria-hidden />
            </button>
          </div>
        </div>

        <textarea
          id="source-text"
          value={sourceText}
          onChange={(e) => onSourceTextChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              if (canTranslate) onTranslate();
            }
          }}
          placeholder={
            fromEnglish
              ? "Type an English sentence to translate…"
              : "Type Kikamba, or tap Speak to say it…"
          }
          className="min-h-[7rem] w-full flex-1 resize-none bg-transparent text-lg leading-relaxed text-neutral-900 placeholder:text-neutral-400 focus:outline-none"
        />

        <div className="mt-3 flex items-center justify-between gap-3">
          <span className={`text-xs ${overLimit ? "font-semibold text-red-600" : "text-neutral-400"}`}>
            {charCount} / {MAX_TRANSLATE_CHARS}
          </span>
          <div className="flex items-center gap-3">
            <kbd className="hidden font-sans text-xs text-neutral-400 sm:inline">
              {isMac ? "⌘" : "Ctrl"} ↵
            </kbd>
            <button
              type="button"
              onClick={() => onTranslate()}
              disabled={!canTranslate}
              className="inline-flex items-center gap-1.5 rounded-lg border border-butter-400 bg-butter-300 px-3 py-1.5 text-sm font-medium text-butter-900 transition hover:bg-butter-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 active:scale-[0.97] disabled:cursor-not-allowed disabled:border-neutral-200 disabled:bg-neutral-50 disabled:text-neutral-400"
            >
              {isTranslating ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Languages className="h-4 w-4" aria-hidden />
              )}
              {isTranslating ? "Translating…" : "Translate"}
            </button>
          </div>
        </div>
      </div>

      {/* Translation */}
      <div className="flex min-h-[15rem] flex-col bg-neutral-50/60 p-4 sm:p-5">
        <div className="mb-3 flex h-7 items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-butter-800">
            {fromEnglish ? "Kikamba" : "English"}
          </span>
          {fromEnglish && kikambaBadge}
        </div>

        <div
          aria-live="polite"
          aria-busy={isTranslating}
          className={`flex-1 text-lg leading-relaxed text-neutral-900 transition-opacity ${
            isTranslating ? "opacity-50" : ""
          }`}
        >
          {translatedText || (
            <span className="text-neutral-400">
              {fromEnglish ? "Kikamba" : "English"} translation will appear here.
            </span>
          )}
          {error && <p className="mt-3 text-sm font-medium text-red-600">{error}</p>}
        </div>

        {fromEnglish && <AudioPlayer key={translatedText} text={translatedText} onError={onNotice} />}
      </div>
    </div>
  );
}
