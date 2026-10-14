"use client";

import { useEffect, useState } from "react";
import { Loader2, PencilLine, X } from "lucide-react";
import { getSuggestions, MAX_TRANSLATE_CHARS, sendCorrection, type CorrectionOrigin, type Direction } from "@/lib/api";

interface CorrectionBoxProps {
  direction: Direction;
  /** The source text and the translation the user marked as poor. */
  source: string;
  translation: string;
  dialect: string;
  onDone: (message: string | null) => void;
}

/**
 * Shown after a thumbs-down: lets the user pick one of the model's other
 * likely translations, edit it, or type the correct one. Corrections become
 * training data once a Kikamba speaker has reviewed them.
 */
export default function CorrectionBox({ direction, source, translation, dialect, onDone }: CorrectionBoxProps) {
  const [suggestions, setSuggestions] = useState<string[] | null>(null);
  const [text, setText] = useState("");
  const [picked, setPicked] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const targetLanguage = direction === "en_to_kam" ? "Kikamba" : "English";

  useEffect(() => {
    let cancelled = false;
    getSuggestions(source, direction, translation)
      .then((s) => !cancelled && setSuggestions(s))
      .catch(() => !cancelled && setSuggestions([]));
    return () => {
      cancelled = true;
    };
  }, [source, direction, translation]);

  function pick(s: string) {
    setPicked(s);
    setText(s);
    setError(null);
  }

  async function handleSend() {
    const correction = text.trim();
    if (!correction) return;
    const origin: CorrectionOrigin = picked === null ? "typed" : correction === picked.trim() ? "suggestion" : "edited";
    setSending(true);
    setError(null);
    try {
      await sendCorrection({ direction, text: source, translation, correction, origin, dialect });
      onDone("Thank you! Your correction will help the translator learn.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't send your correction.");
    } finally {
      setSending(false);
    }
  }

  return (
    <section
      aria-label="Correct this translation"
      className="border-t border-neutral-200 bg-butter-50/60 px-4 py-4 sm:px-6"
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-neutral-900">
            <PencilLine className="h-4 w-4 text-butter-700" aria-hidden />
            Help fix this translation
          </h3>
          <p className="mt-0.5 text-sm text-neutral-600">What is the correct {targetLanguage}?</p>
        </div>
        <button
          type="button"
          aria-label="Close"
          onClick={() => onDone(null)}
          className="-mr-2 -mt-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-neutral-400 transition hover:bg-neutral-100 hover:text-neutral-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>

      <div className="mb-3">
        <p className="mb-1.5 text-xs font-medium uppercase tracking-[0.08em] text-neutral-500">
          Could it be one of these?
        </p>
        {suggestions === null ? (
          <p className="flex items-center gap-2 text-sm text-neutral-500">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            Finding other possible translations…
          </p>
        ) : suggestions.length === 0 ? (
          <p className="text-sm text-neutral-500">No other suggestions. Please type the correct translation below.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {suggestions.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => pick(s)}
                aria-pressed={picked === s}
                className={`min-h-11 rounded-lg border px-3 py-2 text-left text-[15px] transition focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 ${
                  picked === s
                    ? "border-butter-500 bg-butter-100 text-neutral-900"
                    : "border-neutral-200 bg-white text-neutral-800 hover:border-butter-400"
                }`}
              >
                {s}
              </button>
            ))}
            <p className="text-xs text-neutral-500">Tap one to use it, then edit it if it isn&apos;t quite right.</p>
          </div>
        )}
      </div>

      <label className="block">
        <span className="sr-only">Correct translation</span>
        <textarea
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setError(null);
          }}
          rows={3}
          maxLength={MAX_TRANSLATE_CHARS * 2}
          placeholder={`Type the correct ${targetLanguage} translation`}
          className="w-full resize-y rounded-lg border border-neutral-300 bg-white px-3 py-2 text-[15px] text-neutral-900 focus:border-butter-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500/40"
        />
      </label>

      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-md text-xs leading-relaxed text-neutral-500">
          Your correction and the original text are saved without your name. After a Kamba speaker checks them,
          they may be used to train the translator and published as open training data. Please don&apos;t include
          personal details.
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onDone(null)}
            className="inline-flex h-10 items-center rounded-lg px-3 text-sm font-medium text-neutral-600 transition hover:bg-neutral-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500"
          >
            Not now
          </button>
          <button
            type="button"
            onClick={handleSend}
            disabled={!text.trim() || sending}
            className="inline-flex h-10 items-center gap-1.5 rounded-lg border border-butter-400 bg-butter-300 px-4 text-sm font-medium text-butter-900 transition hover:bg-butter-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 disabled:cursor-not-allowed disabled:border-neutral-200 disabled:bg-neutral-50 disabled:text-neutral-400"
          >
            {sending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
            Send correction
          </button>
        </div>
      </div>
    </section>
  );
}
