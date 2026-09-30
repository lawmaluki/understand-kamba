import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import ContributeStudio from "@/components/contribute/ContributeStudio";

export const metadata: Metadata = {
  title: "Lend your voice to Kikamba — Understand Kamba",
  description: "Record Kikamba sentences to help build a real Kamba voice.",
};

export default function ContributePage() {
  return (
    <main className="flex min-h-full flex-1 flex-col bg-gradient-to-b from-butter-100/70 via-neutral-50 to-neutral-50 px-4 pb-24 pt-6 sm:px-6 sm:py-16">
      <div className="mx-auto w-full max-w-3xl">
        <Link
          href="/"
          className="-ml-2 inline-flex h-10 items-center gap-1.5 rounded-md px-2 text-sm font-medium text-neutral-600 transition hover:text-neutral-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          Back to the translator
        </Link>

        <div className="mb-6 mt-4 max-w-xl sm:mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-butter-700">Help build a Kamba voice</p>
          <h1 className="mt-2 text-[2rem] font-medium leading-[1.1] tracking-tight text-neutral-900 sm:text-5xl">
            Lend your voice to Kikamba.
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed text-neutral-500 sm:text-base">
            Translations are read aloud by a Swahili voice today, because no Kikamba voice exists.
            A few minutes of Kikamba speakers reading sentences aloud is what it takes to build one.
          </p>
        </div>

        <ContributeStudio />

        <p className="mt-8 text-xs text-neutral-400">
          Sentences from FLORES-200 by Meta (CC-BY-SA 4.0).
        </p>
      </div>
    </main>
  );
}
