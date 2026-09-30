"use client";

import { useRef, useState } from "react";
import { Loader2, Mic, Square, Upload } from "lucide-react";
import { MAX_RECORDING_SECONDS, transcribeAudio } from "@/lib/api";
import { useRecorder } from "@/lib/useRecorder";

interface VoiceInputProps {
  /** Called with the Kikamba transcript of the recording or uploaded file. */
  onTranscript: (text: string) => void;
  onError: (message: string) => void;
}

export default function VoiceInput({ onTranscript, onError }: VoiceInputProps) {
  const [transcribing, setTranscribing] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function transcribe(blob: Blob, filename: string) {
    setTranscribing(true);
    try {
      const text = await transcribeAudio(blob, filename);
      if (text) onTranscript(text);
      else onError("No speech was recognised in that audio.");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Transcription failed.");
    } finally {
      setTranscribing(false);
    }
  }

  const recorder = useRecorder({
    maxSeconds: MAX_RECORDING_SECONDS,
    onRecorded: (blob, filename) => void transcribe(blob, filename),
    onError,
  });

  const buttonClass =
    "inline-flex h-10 items-center gap-1.5 rounded-md px-2.5 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 disabled:opacity-40 sm:h-8 sm:px-2 sm:text-xs";

  if (transcribing) {
    return (
      <span className="inline-flex h-10 items-center gap-1.5 px-2.5 text-sm text-neutral-500 sm:h-8 sm:px-2 sm:text-xs">
        <Loader2 className="h-4 w-4 animate-spin sm:h-3.5 sm:w-3.5" aria-hidden />
        Transcribing…
      </span>
    );
  }

  if (recorder.recording) {
    return (
      <button
        type="button"
        onClick={recorder.stop}
        className={`${buttonClass} bg-red-50 text-red-700 hover:bg-red-100`}
      >
        <span className="relative flex h-2.5 w-2.5" aria-hidden>
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
          <Square className="relative h-2.5 w-2.5" fill="currentColor" />
        </span>
        Stop · {recorder.seconds}s
      </button>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={recorder.start}
        title="Speak Kikamba to fill in the text"
        className={`${buttonClass} text-butter-700 hover:bg-butter-100`}
      >
        <Mic className="h-4 w-4 sm:h-3.5 sm:w-3.5" aria-hidden />
        Speak
      </button>
      <button
        type="button"
        onClick={() => fileRef.current?.click()}
        aria-label="Upload audio"
        title="Upload a Kikamba audio or video file"
        className={`${buttonClass} w-10 justify-center text-butter-700 hover:bg-butter-100 sm:w-auto`}
      >
        <Upload className="h-4 w-4 sm:h-3.5 sm:w-3.5" aria-hidden />
        <span className="hidden sm:inline">Upload</span>
      </button>
      <input
        ref={fileRef}
        type="file"
        accept="audio/*,video/*"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          e.target.value = ""; // allow re-picking the same file
          if (file) void transcribe(file, file.name);
        }}
      />
    </>
  );
}
