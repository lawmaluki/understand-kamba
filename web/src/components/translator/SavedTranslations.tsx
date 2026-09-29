"use client";

import { useSyncExternalStore } from "react";
import { Trash2 } from "lucide-react";
import { getServerSnapshot, getSnapshot, remove, subscribe } from "@/lib/saved";

export default function SavedTranslations() {
  const items = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  if (items.length === 0) return null;

  return (
    <section className="mt-10" aria-labelledby="saved-heading">
      <div className="mb-3 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 id="saved-heading" className="text-lg font-medium text-neutral-900">
          Saved translations
        </h2>
        <p className="text-sm text-neutral-500">Kept in this browser only.</p>
      </div>
      <ul className="divide-y divide-neutral-200 overflow-hidden rounded-xl border border-neutral-200 bg-white">
        {items.map((item) => {
          const [from, to] = item.direction === "en_to_kam" ? ["EN", "KAM"] : ["KAM", "EN"];
          return (
            <li key={item.id} className="flex items-start gap-3 px-4 py-3">
              <div className="min-w-0 flex-1 space-y-1 text-sm">
                <p className="text-neutral-500">
                  <span className="mr-2 text-[11px] font-semibold tracking-wide text-neutral-400">{from}</span>
                  {item.source}
                </p>
                <p className="text-neutral-900">
                  <span className="mr-2 text-[11px] font-semibold tracking-wide text-butter-700">{to}</span>
                  {item.translation}
                </p>
              </div>
              <button
                type="button"
                aria-label="Remove saved translation"
                onClick={() => remove(item.id)}
                className="-mr-2 inline-flex h-10 w-10 shrink-0 sm:mr-0 sm:h-8 sm:w-8 items-center justify-center rounded-md text-neutral-400 transition hover:bg-neutral-100 hover:text-neutral-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500"
              >
                <Trash2 className="h-4 w-4" aria-hidden />
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
