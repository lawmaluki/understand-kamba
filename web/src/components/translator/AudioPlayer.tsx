"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Pause, Play } from "lucide-react";
import { synthesizeSpeech } from "@/lib/api";

const BAR_COUNT = 48;
const PLACEHOLDER_PEAKS = Array.from({ length: BAR_COUNT }, () => 0.15);

type Status = "idle" | "loading" | "playing" | "paused";

/** Loudest sample in each of `count` equal slices, scaled so the loudest slice is 1. */
async function computePeaks(blob: Blob, count: number): Promise<number[]> {
  const ctx = new AudioContext();
  try {
    const buffer = await ctx.decodeAudioData(await blob.arrayBuffer());
    const data = buffer.getChannelData(0);
    const size = Math.floor(data.length / count) || 1;
    const peaks = Array.from({ length: count }, (_, i) => {
      let max = 0;
      for (let j = i * size; j < Math.min((i + 1) * size, data.length); j++) {
        max = Math.max(max, Math.abs(data[j]));
      }
      return max;
    });
    const top = Math.max(...peaks) || 1;
    return peaks.map((p) => p / top);
  } finally {
    void ctx.close();
  }
}

function formatTime(seconds: number) {
  const s = Math.floor(seconds);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

interface AudioPlayerProps {
  /** Kikamba text to read. Remount (key on the text) to reset for new text. */
  text: string;
  onError: (message: string) => void;
}

export default function AudioPlayer({ text, onError }: AudioPlayerProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [peaks, setPeaks] = useState<number[] | null>(null);
  const [duration, setDuration] = useState(0);
  const [current, setCurrent] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const urlRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    };
  }, []);

  async function load(): Promise<HTMLAudioElement> {
    const blob = await synthesizeSpeech(text);
    const p = await computePeaks(blob, BAR_COUNT).catch(() => null); // waveform is cosmetic
    const url = URL.createObjectURL(blob);
    urlRef.current = url;

    const audio = new Audio(url);
    audio.ontimeupdate = () => setCurrent(audio.currentTime);
    audio.onloadedmetadata = () => setDuration(audio.duration);
    audio.onended = () => {
      setStatus("idle");
      setCurrent(0);
    };
    audioRef.current = audio;
    setPeaks(p);
    return audio;
  }

  async function toggle() {
    if (status === "loading") return;
    if (status === "playing") {
      audioRef.current?.pause();
      setStatus("paused");
      return;
    }
    try {
      let audio = audioRef.current;
      if (!audio) {
        setStatus("loading");
        audio = await load();
      }
      await audio.play();
      setStatus("playing");
    } catch (err) {
      setStatus("idle");
      onError(err instanceof Error ? err.message : "Couldn't play the audio.");
    }
  }

  const progress = duration ? current / duration : 0;
  const bars = peaks ?? PLACEHOLDER_PEAKS;
  const label =
    status === "playing" ? "Pause" : status === "loading" ? "Generating audio…" : "Play Kikamba audio";

  return (
    <div className="mt-4">
      <div className="flex items-center gap-3">
        <button
          type="button"
          aria-label={label}
          title={label}
          onClick={toggle}
          disabled={!text}
          className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full sm:h-9 sm:w-9 border border-butter-400 bg-butter-300 text-butter-900 transition hover:bg-butter-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 active:scale-95 disabled:cursor-not-allowed disabled:border-neutral-200 disabled:bg-neutral-100 disabled:text-neutral-400"
        >
          {status === "loading" ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          ) : status === "playing" ? (
            <Pause className="h-4 w-4" fill="currentColor" aria-hidden />
          ) : (
            <Play className="h-4 w-4 translate-x-[1px]" fill="currentColor" aria-hidden />
          )}
        </button>
        {/* Bars shrink (down to hairlines) instead of overflowing on narrow screens. */}
        <div aria-hidden className="flex h-6 min-w-0 flex-1 items-center justify-between gap-[2px] sm:gap-[3px]">
          {bars.map((p, i) => (
            <span
              key={i}
              className={`min-w-px max-w-[3px] flex-1 rounded-full transition-colors ${
                peaks && i / bars.length < progress ? "bg-butter-600" : "bg-neutral-300"
              }`}
              style={{ height: `${Math.max(3, Math.round(p * 22))}px` }}
            />
          ))}
        </div>
        <span className="shrink-0 text-xs tabular-nums text-neutral-400">
          {formatTime(current)} / {formatTime(duration)}
        </span>
      </div>
      <p className="mt-1.5 text-[11px] text-neutral-400">
        Read by a Swahili voice &mdash; no Kikamba voice model exists yet.
      </p>
    </div>
  );
}
