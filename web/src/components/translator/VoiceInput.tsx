"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Mic, Square, Upload } from "lucide-react";
import { MAX_RECORDING_SECONDS, transcribeAudio } from "@/lib/api";

type Status = "idle" | "recording" | "transcribing";

function extensionFor(mimeType: string) {
  if (mimeType.includes("mp4")) return "m4a";
  if (mimeType.includes("ogg")) return "ogg";
  return "webm";
}

interface VoiceInputProps {
  /** Called with the Kikamba transcript of the recording or uploaded file. */
  onTranscript: (text: string) => void;
  onError: (message: string) => void;
}

export default function VoiceInput({ onTranscript, onError }: VoiceInputProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [seconds, setSeconds] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function stopTimer() {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
  }

  useEffect(() => {
    return () => {
      stopTimer();
      const rec = recorderRef.current;
      if (rec && rec.state !== "inactive") {
        rec.onstop = null; // unmounting: don't transcribe
        rec.stop();
        rec.stream.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  async function transcribe(blob: Blob, filename: string) {
    setStatus("transcribing");
    try {
      const text = await transcribeAudio(blob, filename);
      if (text) onTranscript(text);
      else onError("No speech was recognised in that audio.");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Transcription failed.");
    } finally {
      setStatus("idle");
    }
  }

  async function startRecording() {
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      onError("Microphone access was blocked. Allow it in your browser to record.");
      return;
    }
    const recorder = new MediaRecorder(stream);
    const chunks: Blob[] = [];
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = () => {
      stopTimer();
      stream.getTracks().forEach((t) => t.stop());
      const type = recorder.mimeType || "audio/webm";
      void transcribe(new Blob(chunks, { type }), `recording.${extensionFor(type)}`);
    };
    recorderRef.current = recorder;
    recorder.start();
    setSeconds(0);
    setStatus("recording");
    const startedAt = Date.now();
    timerRef.current = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      setSeconds(elapsed);
      if (elapsed >= MAX_RECORDING_SECONDS) recorder.stop();
    }, 250);
  }

  const buttonClass =
    "inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 disabled:opacity-40";

  if (status === "transcribing") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-1 text-xs text-neutral-500">
        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
        Transcribing…
      </span>
    );
  }

  if (status === "recording") {
    return (
      <button
        type="button"
        onClick={() => recorderRef.current?.stop()}
        className={`${buttonClass} bg-red-50 text-red-700 hover:bg-red-100`}
      >
        <Square className="h-3 w-3" fill="currentColor" aria-hidden />
        Stop · {seconds}s
      </button>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={startRecording}
        title="Speak Kikamba to fill in the text"
        className={`${buttonClass} text-butter-700 hover:bg-butter-100`}
      >
        <Mic className="h-3.5 w-3.5" aria-hidden />
        Speak
      </button>
      <button
        type="button"
        onClick={() => fileRef.current?.click()}
        title="Upload a Kikamba audio or video file"
        className={`${buttonClass} text-butter-700 hover:bg-butter-100`}
      >
        <Upload className="h-3.5 w-3.5" aria-hidden />
        Upload
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
