"use client";

import { useState } from "react";
import { Bookmark, Check, Copy, Share2, ThumbsDown, ThumbsUp } from "lucide-react";
import type { Direction } from "@/lib/api";
import { save } from "@/lib/saved";

export type Rating = "up" | "down";

interface FooterControlsProps {
  direction: Direction;
  /** The source text that produced `translation` (not the live textarea). */
  source: string;
  translation: string;
  rating: Rating | null;
  onRate: (rating: Rating) => void;
  onNotice: (message: string) => void;
}

export default function FooterControls({
  direction,
  source,
  translation,
  rating,
  onRate,
  onNotice,
}: FooterControlsProps) {
  const [copied, setCopied] = useState(false);
  const hasTranslation = !!translation;
  const [from, to] = direction === "en_to_kam" ? ["English", "Kikamba"] : ["Kikamba", "English"];

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(translation);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      onNotice("Couldn't copy to clipboard -- your browser may have blocked it.");
    }
  }

  async function handleShare() {
    const text = `${from}: ${source}\n${to}: ${translation}`;
    if (navigator.share) {
      try {
        await navigator.share({ title: `${from} → ${to} translation`, text });
      } catch {
        // Share sheet dismissed -- nothing to do.
      }
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      onNotice("Copied both texts -- paste them wherever you want to share.");
    } catch {
      onNotice("Couldn't copy to clipboard -- your browser may have blocked it.");
    }
  }

  function handleSave() {
    onNotice(
      save({ direction, source, translation })
        ? "Saved -- find it under Saved translations below."
        : "This translation is already saved."
    );
  }

  const iconButtonClass =
    "inline-flex h-10 w-10 items-center justify-center rounded-md sm:h-8 sm:w-8 text-neutral-500 transition hover:bg-neutral-100 hover:text-neutral-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 active:scale-[0.95] disabled:pointer-events-none disabled:opacity-40";
  const ratedClass = "bg-butter-200 text-butter-900 hover:bg-butter-200 hover:text-butter-900";

  return (
    <div className="flex items-center gap-1 px-2 py-1.5 sm:px-4 sm:py-2.5">
      <button
        type="button"
        aria-label="Copy translation"
        onClick={handleCopy}
        disabled={!hasTranslation}
        className={iconButtonClass}
      >
        {copied ? <Check className="h-4 w-4 text-emerald-600" aria-hidden /> : <Copy className="h-4 w-4" aria-hidden />}
      </button>
      <button type="button" aria-label="Share" onClick={handleShare} disabled={!hasTranslation} className={iconButtonClass}>
        <Share2 className="h-4 w-4" aria-hidden />
      </button>
      <button
        type="button"
        aria-label="Save translation"
        onClick={handleSave}
        disabled={!hasTranslation}
        className={iconButtonClass}
      >
        <Bookmark className="h-4 w-4" aria-hidden />
      </button>

      {/* On phones the rating buttons sit at the far right, without the label. */}
      <span aria-hidden className="mx-2 hidden h-4 w-px bg-neutral-200 sm:block" />

      <div className="ml-auto flex items-center gap-1 sm:ml-0">
        <span className="mr-1 hidden text-xs text-neutral-500 sm:inline">
          {rating ? "Thanks for rating" : "Rate this translation"}
        </span>
        {(["up", "down"] as const).map((r) => {
          const Icon = r === "up" ? ThumbsUp : ThumbsDown;
          return (
            <button
              key={r}
              type="button"
              aria-label={r === "up" ? "Good translation" : "Poor translation"}
              aria-pressed={rating === r}
              onClick={() => onRate(r)}
              disabled={!hasTranslation || rating !== null}
              className={`${iconButtonClass} ${rating === r ? `${ratedClass} disabled:opacity-100` : ""}`}
            >
              <Icon className="h-4 w-4" aria-hidden />
            </button>
          );
        })}
      </div>
    </div>
  );
}
