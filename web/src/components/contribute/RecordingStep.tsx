"use client";

import { useEffect, useState } from "react";
import { Check, Loader2, Mic, RotateCcw, SkipForward, Square } from "lucide-react";
import { submitVoiceRecording, type VoicePrompt } from "@/lib/api";
import { editProfile, markRecorded, type ContributorProfile } from "@/lib/contributor";
import { useRecorder } from "@/lib/useRecorder";

const DELETION_URL = "https://github.com/lawmaluki/understand-kamba/issues/new";

interface Take {
  blob: Blob;
  filename: string;
  url: string;
}

interface RecordingStepProps {
  prompts: VoicePrompt[];
  maxSeconds: number;
  profile: ContributorProfile;
  recorded: string[];
}

function pickPrompt(prompts: VoicePrompt[], exclude: Set<string>): VoicePrompt | null {
  const open = prompts.filter((p) => !exclude.has(p.id));
  return open.length ? open[Math.floor(Math.random() * open.length)] : null;
}

export default function RecordingStep({ prompts, maxSeconds, profile, recorded }: RecordingStepProps) {
  const [skipped, setSkipped] = useState<Set<string>>(() => new Set());
  const [prompt, setPrompt] = useState(() => pickPrompt(prompts, new Set(recorded)));
  const [take, setTake] = useState<Take | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const recorder = useRecorder({
    maxSeconds,
    onRecorded: (blob, filename) => setTake({ blob, filename, url: URL.createObjectURL(blob) }),
    onError: (text) => setMessage({ kind: "error", text }),
  });

  // Free each take's audio URL once it's replaced or the page closes.
  useEffect(() => () => {
    if (take) URL.revokeObjectURL(take.url);
  }, [take]);

  function next(skip = false) {
    const exclude = new Set([...recorded, ...skipped]);
    if (prompt) exclude.add(prompt.id);
    if (skip && prompt) setSkipped((s) => new Set(s).add(prompt.id));
    setTake(null);
    setPrompt(pickPrompt(prompts, exclude));
  }

  async function submit() {
    if (!take || !prompt) return;
    setUploading(true);
    setMessage(null);
    try {
      await submitVoiceRecording(take.blob, take.filename, prompt.id, profile);
      markRecorded(prompt.id);
      setMessage({ kind: "ok", text: "Saved — thank you! Here's the next sentence." });
      next();
    } catch (err) {
      setMessage({ kind: "error", text: err instanceof Error ? err.message : "Couldn't save the recording." });
    } finally {
      setUploading(false);
    }
  }

  const count = recorded.length;
  const deletionLink =
    `${DELETION_URL}?title=${encodeURIComponent("Delete my voice recordings")}` +
    `&body=${encodeURIComponent(`Contributor ID: ${profile.speakerId}`)}`;

  return (
    <div>
      <div className="flex items-center justify-between gap-3 border-b border-neutral-200 px-4 py-3 sm:px-6">
        <p className="text-sm text-neutral-600">
          <span className="font-semibold text-neutral-900">{count}</span> sentence{count === 1 ? "" : "s"} recorded
          {count > 0 && " — thank you!"}
        </p>
        <button
          type="button"
          onClick={() => next(true)}
          disabled={!prompt || recorder.recording || uploading}
          className="-mr-2 inline-flex h-10 items-center gap-1.5 rounded-md px-3 text-sm font-medium text-neutral-600 transition hover:bg-neutral-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 disabled:opacity-40"
        >
          <SkipForward className="h-4 w-4" aria-hidden />
          Skip
        </button>
      </div>

      <div className="px-4 py-8 sm:px-6 sm:py-10">
        {prompt ? (
          <>
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-butter-800">Read this aloud</p>
            <p lang="kam" className="mt-3 text-2xl leading-snug text-neutral-900 sm:text-[28px]">
              {prompt.text}
            </p>
          </>
        ) : (
          <p className="text-lg text-neutral-700">
            You&apos;ve been through every sentence — thank you for all your recordings!
          </p>
        )}

        <div className="mt-8 flex min-h-[4.5rem] flex-wrap items-center gap-3" aria-live="polite">
          {recorder.recording ? (
            <>
              <button
                type="button"
                onClick={recorder.stop}
                aria-label="Stop recording"
                className="relative inline-flex h-16 w-16 items-center justify-center rounded-full bg-red-600 text-white shadow transition hover:bg-red-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-2"
              >
                <span className="absolute inset-0 animate-ping rounded-full bg-red-400 opacity-30" aria-hidden />
                <Square className="relative h-6 w-6" fill="currentColor" aria-hidden />
              </button>
              <span className="text-sm tabular-nums text-neutral-700">
                Recording… {recorder.seconds}s / {maxSeconds}s
              </span>
            </>
          ) : take ? (
            <>
              <audio controls src={take.url} className="h-11 w-full max-w-sm" />
              <div className="flex w-full flex-wrap gap-2 sm:w-auto">
                <button
                  type="button"
                  onClick={() => {
                    setTake(null);
                    void recorder.start();
                  }}
                  disabled={uploading}
                  className="inline-flex h-11 flex-1 items-center justify-center gap-1.5 rounded-lg border border-neutral-300 bg-white px-4 text-[15px] font-medium text-neutral-800 transition hover:bg-neutral-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 disabled:opacity-40 sm:flex-none"
                >
                  <RotateCcw className="h-4 w-4" aria-hidden />
                  Re-record
                </button>
                <button
                  type="button"
                  onClick={submit}
                  disabled={uploading}
                  className="inline-flex h-11 flex-1 items-center justify-center gap-1.5 rounded-lg border border-butter-400 bg-butter-300 px-5 text-[15px] font-medium text-butter-900 transition hover:bg-butter-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 disabled:opacity-60 sm:flex-none"
                >
                  {uploading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Check className="h-4 w-4" aria-hidden />}
                  {uploading ? "Saving…" : "Submit"}
                </button>
              </div>
            </>
          ) : (
            prompt && (
              <>
                <button
                  type="button"
                  onClick={() => {
                    setMessage(null);
                    void recorder.start();
                  }}
                  aria-label="Start recording"
                  className="inline-flex h-16 w-16 items-center justify-center rounded-full border border-butter-400 bg-butter-300 text-butter-900 shadow-sm transition hover:bg-butter-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 focus-visible:ring-offset-2 active:scale-95"
                >
                  <Mic className="h-7 w-7" aria-hidden />
                </button>
                <span className="text-sm text-neutral-600">Tap to record, then tap again to stop.</span>
              </>
            )
          )}
        </div>

        {message && (
          <p className={`mt-4 text-sm font-medium ${message.kind === "ok" ? "text-emerald-700" : "text-red-600"}`}>
            {message.text}
          </p>
        )}

        <ul className="mt-8 list-disc space-y-1 pl-5 text-sm text-neutral-500">
          <li>Read naturally, at your normal pace, somewhere quiet.</li>
          <li>Skip any sentence you&apos;re not sure how to read.</li>
          <li>Each recording can be up to {maxSeconds} seconds.</li>
        </ul>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-neutral-200 px-4 py-3 text-xs text-neutral-500 sm:px-6">
        <span>
          Contributor ID: <span className="font-mono text-neutral-700">{profile.speakerId.slice(0, 8)}</span>
        </span>
        <button type="button" onClick={editProfile} className="min-h-10 underline-offset-2 hover:underline">
          Change my details
        </button>
        <a href={deletionLink} target="_blank" rel="noreferrer" className="min-h-10 content-center underline-offset-2 hover:underline">
          Ask to delete my recordings
        </a>
      </div>
    </div>
  );
}
