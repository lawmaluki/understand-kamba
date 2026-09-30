"use client";

import { useCallback, useEffect, useRef, useState } from "react";

function extensionFor(mimeType: string) {
  if (mimeType.includes("mp4")) return "m4a";
  if (mimeType.includes("ogg")) return "ogg";
  return "webm";
}

interface UseRecorderOptions {
  /** Recording stops by itself after this many seconds. */
  maxSeconds: number;
  onRecorded: (audio: Blob, filename: string) => void;
  onError: (message: string) => void;
}

/** Microphone recording with an elapsed-seconds counter and an automatic time limit. */
export function useRecorder({ maxSeconds, onRecorded, onError }: UseRecorderOptions) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Latest callbacks, so a recording in progress never calls a stale one.
  const callbacks = useRef({ onRecorded, onError });
  useEffect(() => {
    callbacks.current = { onRecorded, onError };
  });

  const stopTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
  };

  useEffect(() => {
    return () => {
      stopTimer();
      const rec = recorderRef.current;
      if (rec && rec.state !== "inactive") {
        rec.onstop = null; // unmounting: discard the recording
        rec.stop();
        rec.stream.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  const start = useCallback(async () => {
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      callbacks.current.onError("Microphone access was blocked. Allow it in your browser to record.");
      return;
    }
    const recorder = new MediaRecorder(stream);
    const chunks: Blob[] = [];
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = () => {
      stopTimer();
      setRecording(false);
      stream.getTracks().forEach((t) => t.stop());
      const type = recorder.mimeType || "audio/webm";
      callbacks.current.onRecorded(new Blob(chunks, { type }), `recording.${extensionFor(type)}`);
    };
    recorderRef.current = recorder;
    recorder.start();
    setSeconds(0);
    setRecording(true);
    const startedAt = Date.now();
    timerRef.current = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      setSeconds(elapsed);
      if (elapsed >= maxSeconds) recorder.stop();
    }, 250);
  }, [maxSeconds]);

  const stop = useCallback(() => {
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
  }, []);

  return { recording, seconds, start, stop };
}
