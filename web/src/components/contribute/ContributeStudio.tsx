"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { Loader2 } from "lucide-react";
import { getVoicePrompts, type VoicePrompts } from "@/lib/api";
import { getServerSnapshot, getSnapshot, saveProfile, subscribe } from "@/lib/contributor";
import ConsentStep from "./ConsentStep";
import RecordingStep from "./RecordingStep";

export default function ContributeStudio() {
  const contributor = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const [data, setData] = useState<VoicePrompts | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    getVoicePrompts()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Couldn't load the sentences."));
  }, []);

  useEffect(load, [load]);

  // Re-ask for consent whenever its wording (version) changes on the server.
  const consented = data && contributor.profile?.consentVersion === data.consent_version;

  return (
    <div className="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-[0_24px_60px_-30px_rgba(140,107,18,0.22)]">
      {error ? (
        <div className="space-y-3 p-6">
          <p className="text-sm font-medium text-red-600">{error}</p>
          <button
            type="button"
            onClick={() => {
              setError(null);
              load();
            }}
            className="inline-flex h-10 items-center rounded-lg border border-neutral-300 px-4 text-sm font-medium text-neutral-800 hover:bg-neutral-50"
          >
            Try again
          </button>
        </div>
      ) : !data ? (
        <p className="flex items-center gap-2 p-6 text-sm text-neutral-500">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Loading sentences…
        </p>
      ) : consented && contributor.profile ? (
        <RecordingStep
          prompts={data.prompts}
          maxSeconds={data.max_seconds}
          profile={contributor.profile}
          recorded={contributor.recorded}
        />
      ) : (
        <ConsentStep consentVersion={data.consent_version} existing={contributor.profile} onAgree={saveProfile} />
      )}
    </div>
  );
}
