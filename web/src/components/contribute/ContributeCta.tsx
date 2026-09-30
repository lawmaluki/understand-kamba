import Link from "next/link";
import { ArrowRight, Mic } from "lucide-react";

/** Home-page invitation to the voice-recording page. */
export default function ContributeCta() {
  return (
    <section
      aria-labelledby="contribute-heading"
      className="mt-10 flex flex-col gap-4 rounded-2xl border border-butter-300 bg-butter-50 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6"
    >
      <div className="flex gap-4">
        <div
          aria-hidden
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-butter-400 bg-butter-300 text-butter-900"
        >
          <Mic className="h-5 w-5" />
        </div>
        <div>
          <h2 id="contribute-heading" className="text-lg font-medium text-neutral-900">
            Speak Kikamba? Help build a real Kamba voice.
          </h2>
          <p className="mt-1 max-w-xl text-sm leading-relaxed text-neutral-600">
            Today&apos;s voice is Swahili. Read a few Kikamba sentences aloud and your recordings
            will help train a voice that truly sounds Kamba.
          </p>
        </div>
      </div>
      <Link
        href="/contribute"
        className="inline-flex h-11 shrink-0 items-center justify-center gap-1.5 rounded-lg border border-butter-400 bg-butter-300 px-5 text-[15px] font-medium text-butter-900 transition hover:bg-butter-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500"
      >
        Record your voice
        <ArrowRight className="h-4 w-4" aria-hidden />
      </Link>
    </section>
  );
}
