"use client";

import { CircleCheck } from "lucide-react";
import { DIALECTS } from "@/lib/dialects";

interface DialectSelectorProps {
  selectedId: string;
  onSelect: (id: string) => void;
}

export default function DialectSelector({ selectedId, onSelect }: DialectSelectorProps) {
  return (
    <section className="mt-10" aria-labelledby="dialects-heading">
      <h2 id="dialects-heading" className="mb-3 text-lg font-medium text-neutral-900">
        Dialects &amp; voices
      </h2>

      {/* Phones: a swipeable row that bleeds to the screen edges. Wider: a grid. */}
      <div
        role="radiogroup"
        aria-labelledby="dialects-heading"
        className="no-scrollbar -mx-4 flex snap-x snap-mandatory scroll-px-4 gap-3 overflow-x-auto px-4 pb-1 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-visible sm:px-0 lg:grid-cols-4"
      >
        {DIALECTS.map((dialect) => {
          const selected = dialect.id === selectedId;
          return (
            <button
              key={dialect.id}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onSelect(dialect.id)}
              className={`relative w-[75%] shrink-0 snap-start rounded-xl border p-4 text-left transition sm:w-auto focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 ${
                selected
                  ? "border-butter-400 bg-butter-50 shadow-[0_0_0_3px_rgba(248,226,122,0.35)]"
                  : "border-neutral-200 bg-white hover:border-butter-300 hover:bg-butter-50/40"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-[15px] font-semibold text-neutral-900">{dialect.label}</p>
                {selected && <CircleCheck className="h-4 w-4 shrink-0 text-butter-700" aria-hidden />}
              </div>
              <p className="mt-1.5 text-sm leading-snug text-neutral-500">{dialect.description}</p>
            </button>
          );
        })}
      </div>
    </section>
  );
}
