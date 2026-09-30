"use client";

import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import type { ContributorProfile } from "@/lib/contributor";

const DIALECTS = [
  { id: "machakos", label: "Machakos" },
  { id: "kitui", label: "Kitui" },
  { id: "makueni", label: "Makueni" },
  { id: "other", label: "Other / not sure" },
];
const GENDERS = [
  { id: "", label: "Prefer not to say" },
  { id: "female", label: "Female" },
  { id: "male", label: "Male" },
  { id: "other", label: "Other" },
];
const AGE_RANGES = [
  { id: "", label: "Prefer not to say" },
  { id: "18-29", label: "18–29" },
  { id: "30-44", label: "30–44" },
  { id: "45-59", label: "45–59" },
  { id: "60+", label: "60+" },
];

interface ConsentStepProps {
  consentVersion: string;
  existing: ContributorProfile | null;
  onAgree: (details: Omit<ContributorProfile, "speakerId">) => void;
}

const selectClass =
  "h-11 w-full rounded-lg border border-neutral-300 bg-white px-3 text-[15px] text-neutral-900 focus:border-butter-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500/40";

export default function ConsentStep({ consentVersion, existing, onAgree }: ConsentStepProps) {
  const [dialect, setDialect] = useState(existing?.dialect ?? "");
  const [gender, setGender] = useState(existing?.gender ?? "");
  const [ageRange, setAgeRange] = useState(existing?.ageRange ?? "");
  const [adult, setAdult] = useState(false);
  const [fluent, setFluent] = useState(false);
  const [agree, setAgree] = useState(false);
  const ready = dialect && adult && fluent && agree;

  const checks = [
    { checked: adult, set: setAdult, label: "I am 18 or older." },
    { checked: fluent, set: setFluent, label: "I speak Kikamba fluently." },
    {
      checked: agree,
      set: setAgree,
      label: "I agree to my recordings being used as described above.",
    },
  ];

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (ready) onAgree({ dialect, gender, ageRange, consentVersion });
      }}
      className="space-y-6 p-4 sm:p-6"
    >
      <div className="rounded-xl border border-butter-300 bg-butter-50 p-4 text-sm leading-relaxed text-neutral-700">
        <p className="mb-2 flex items-center gap-2 font-semibold text-neutral-900">
          <ShieldCheck className="h-4 w-4 text-butter-700" aria-hidden />
          How your recordings are used
        </p>
        <ul className="list-disc space-y-1.5 pl-5">
          <li>
            You&apos;ll read Kikamba sentences aloud. Each recording, the sentence and the details
            below are stored in a <strong>private dataset</strong> held by the Understand Kamba
            project.
          </li>
          <li>
            They&apos;re used to build and test Kamba speech technology, starting with a real
            Kikamba voice for reading translations aloud. Models trained on them may be shared
            publicly.
          </li>
          <li>
            We don&apos;t ask for your name or contact details. You get an anonymous contributor ID,
            which you can use to ask for your recordings to be deleted at any time.
          </li>
        </ul>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-neutral-800">
            Your Kikamba dialect <span className="text-red-600">*</span>
          </span>
          <select required value={dialect} onChange={(e) => setDialect(e.target.value)} className={selectClass}>
            <option value="" disabled>
              Choose…
            </option>
            {DIALECTS.map((d) => (
              <option key={d.id} value={d.id}>
                {d.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-neutral-800">Gender (optional)</span>
          <select value={gender} onChange={(e) => setGender(e.target.value)} className={selectClass}>
            {GENDERS.map((g) => (
              <option key={g.id} value={g.id}>
                {g.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-neutral-800">Age (optional)</span>
          <select value={ageRange} onChange={(e) => setAgeRange(e.target.value)} className={selectClass}>
            {AGE_RANGES.map((a) => (
              <option key={a.id} value={a.id}>
                {a.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="-mt-2 text-xs text-neutral-500">
        Dialect, gender and age help a voice model sound natural and let us check it works well for
        everyone.
      </p>

      <fieldset className="space-y-2">
        <legend className="sr-only">Confirmations</legend>
        {checks.map((c) => (
          <label key={c.label} className="flex min-h-11 cursor-pointer items-start gap-3 rounded-lg px-1 py-2">
            <input
              type="checkbox"
              checked={c.checked}
              onChange={(e) => c.set(e.target.checked)}
              className="mt-0.5 h-5 w-5 shrink-0 accent-butter-600"
            />
            <span className="text-[15px] text-neutral-800">{c.label}</span>
          </label>
        ))}
      </fieldset>

      <button
        type="submit"
        disabled={!ready}
        className="inline-flex h-11 w-full items-center justify-center rounded-lg border border-butter-400 bg-butter-300 px-5 text-[15px] font-medium text-butter-900 transition hover:bg-butter-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 disabled:cursor-not-allowed disabled:border-neutral-200 disabled:bg-neutral-100 disabled:text-neutral-400 sm:w-auto"
      >
        Start recording
      </button>
    </form>
  );
}
