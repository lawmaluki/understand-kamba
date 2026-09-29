"use client";

import { AudioLines } from "lucide-react";
import type { Direction, Stats } from "@/lib/api";

const DIRECTIONS: { id: Direction; label: string }[] = [
  { id: "en_to_kam", label: "English → Kikamba" },
  { id: "kam_to_en", label: "Kikamba → English" },
];

function statsLine(stats: Stats | null): string[] {
  if (!stats) return [];
  const rated = stats.ratings_up + stats.ratings_down;
  return [
    `${stats.translations.toLocaleString()} translation${stats.translations === 1 ? "" : "s"}`,
    rated
      ? `${Math.round((stats.ratings_up / rated) * 100)}% rated helpful (${rated.toLocaleString()})`
      : "No ratings yet",
  ];
}

interface StudioHeaderProps {
  dialectLabel: string;
  stats: Stats | null;
  direction: Direction;
  onDirectionChange: (direction: Direction) => void;
}

export default function StudioHeader({
  dialectLabel,
  stats,
  direction,
  onDirectionChange,
}: StudioHeaderProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 border-b border-neutral-200 px-4 py-4 sm:px-5">
      <div className="flex min-w-0 items-center gap-3">
        <div
          aria-hidden
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-butter-400 bg-butter-300 text-butter-900"
        >
          <AudioLines className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold text-neutral-900">{dialectLabel}</h2>
          <p className="mt-0.5 flex flex-wrap gap-x-3 text-xs text-neutral-500">
            {statsLine(stats).map((s) => (
              <span key={s}>{s}</span>
            ))}
          </p>
        </div>
      </div>

      <div
        role="radiogroup"
        aria-label="Translation direction"
        className="inline-flex rounded-lg border border-neutral-200 p-0.5"
      >
        {DIRECTIONS.map((d) => {
          const active = direction === d.id;
          return (
            <button
              key={d.id}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => !active && onDirectionChange(d.id)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 ${
                active
                  ? "bg-butter-300 text-butter-900 ring-1 ring-inset ring-butter-400"
                  : "text-neutral-600 hover:text-neutral-900"
              }`}
            >
              {d.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
