"use client";

import { useLayoutEffect, useRef, useState, useSyncExternalStore } from "react";
import { Languages, Loader2, Shuffle, X } from "lucide-react";
import { MAX_TRANSLATE_CHARS, type Direction, type Voice } from "@/lib/api";
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
  const [voice, setVoice] = useState<Voice>("female"); // kept across translations
  const isMac = useSyncExternalStore(
    noopSubscribe,
    () => /Mac|iPhone|iPad/.test(navigator.platform),
    () => false
  );

  // Grow the text box with its content (up to ~60% of the screen) so long
  // text doesn't have to be scrolled inside a small box on phones.
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, window.innerHeight * 0.6)}px`;
  }, [sourceText]);

  const kikambaBadge = (
    <span className="rounded-md bg-butter-200 px-1.5 py-0.5 text-[11px] font-medium text-butter-900">
      {dialectShort}
    </span>
  );

  return (
    // grid-cols-1 (minmax(0, 1fr)) stops wide content like the waveform from
    // stretching the panels past the card on narrow phones.
    <div className="grid grid-cols-1 border-b border-neutral-200 md:grid-cols-2">
      {/* Source */}
      <div className="flex min-h-[12rem] flex-col border-b border-neutral-200 p-4 sm:p-5 md:min-h-[15rem] md:border-b-0 md:border-r">
        <div className="mb-2 flex h-8 items-center justify-between gap-2 sm:mb-3">
          <div className="flex min-w-0 items-center gap-2">
            <label
              htmlFor="source-text"
              className="text-xs font-semibold uppercase tracking-[0.12em] text-neutral-500"
            >
              {fromEnglish ? "English" : "Kikamba"}
            </label>
            {!fromEnglish && kikambaBadge}
          </div>
          <div className="flex items-center gap-1">
            <span className={`text-xs tabular-nums ${overLimit ? "font-semibold text-red-600" : "text-neutral-400"}`}>
              {charCount} / {MAX_TRANSLATE_CHARS}
            </span>
            <button
              type="button"
              aria-label="Clear text"
              onClick={() => onSourceTextChange("")}
              disabled={!sourceText}
              className="-mr-2 inline-flex h-10 w-10 items-center justify-center rounded-md text-neutral-400 transition hover:bg-neutral-100 hover:text-neutral-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 disabled:opacity-40 sm:mr-0 sm:h-7 sm:w-7"
            >
              <X className="h-4 w-4 sm:h-3.5 sm:w-3.5" aria-hidden />
            </button>
          </div>
        </div>

        <textarea
          id="source-text"
          ref={textareaRef}
          rows={3}
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
          // 18px text: at 16px or more, iOS doesn't zoom the page when the box is focused.
          className="min-h-[5.5rem] w-full resize-none bg-transparent text-lg leading-relaxed text-neutral-900 placeholder:text-neutral-400 focus:outline-none md:min-h-[7rem] md:flex-1"
        />

        <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
          <div className="-ml-2 flex items-center gap-1">
            {fromEnglish ? (
              <button
                type="button"
                onClick={() => onSourceTextChange(pickSample(sourceText))}
                className="inline-flex h-10 items-center gap-1.5 rounded-md px-2 text-sm font-medium text-butter-700 transition hover:bg-butter-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 sm:h-8 sm:text-xs"
              >
                <Shuffle className="h-4 w-4 sm:h-3.5 sm:w-3.5" aria-hidden />
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
          </div>
          <div className="ml-auto flex items-center gap-3">
            <kbd className="hidden font-sans text-xs text-neutral-400 md:inline">
              {isMac ? "⌘" : "Ctrl"} ↵
            </kbd>
            <button
              type="button"
              onClick={() => onTranslate()}
              disabled={!canTranslate}
              className="inline-flex h-10 items-center gap-1.5 rounded-lg border border-butter-400 bg-butter-300 px-4 text-sm font-medium text-butter-900 transition hover:bg-butter-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 active:scale-[0.97] disabled:cursor-not-allowed disabled:border-neutral-200 disabled:bg-neutral-50 disabled:text-neutral-400 sm:h-9 sm:px-3"
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
      <div
        id="translation-output"
        className="flex min-h-[10rem] scroll-mt-4 flex-col bg-neutral-50/60 p-4 sm:p-5 md:min-h-[15rem]"
      >
        <div className="mb-2 flex h-8 items-center gap-2 sm:mb-3">
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

        {fromEnglish && (
          <AudioPlayer
            key={`${voice}:${translatedText}`}
            text={translatedText}
            voice={voice}
            onVoiceChange={setVoice}
            onError={onNotice}
          />
        )}
      </div>
    </div>
  );
}
