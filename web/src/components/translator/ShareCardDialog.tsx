"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { AudioLines, Check, Copy, Download, Files, Loader2, Share2, X } from "lucide-react";
import type { Direction } from "@/lib/api";
import { CARD_SIZES, renderShareCard, SITE_URL, type CardFormat } from "@/lib/shareCard";

interface ShareCardDialogProps {
  open: boolean;
  onClose: () => void;
  direction: Direction;
  source: string;
  translation: string;
  onNotice: (message: string) => void;
}

interface Rendered {
  key: string;
  blob: Blob;
  url: string;
}

const FILE_NAME = "understand-kamba-translation.png";
const noopSubscribe = () => () => {};

export default function ShareCardDialog({ open, onClose, direction, source, translation, onNotice }: ShareCardDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [format, setFormat] = useState<CardFormat>("post");
  const [rendered, setRendered] = useState<Rendered | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [copied, setCopied] = useState<"image" | "text" | null>(null);

  const key = `${format}|${direction}|${source}|${translation}`;
  const ready = rendered?.key === key ? rendered : null;
  const shareText = `${source}\n→ ${translation}\n\nTranslated with Understand Kamba · ${SITE_URL}`;

  // Open/close the native dialog (gives Esc-to-close and focus trapping for free).
  useEffect(() => {
    const d = dialogRef.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  // Draw the card whenever it's open and its content or format changes.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    renderShareCard({ source, translation, direction, format })
      .then((blob) => {
        if (cancelled) return;
        setFailed(null);
        setRendered({ key, blob, url: URL.createObjectURL(blob) }); // the old URL is freed below
      })
      .catch((err) => !cancelled && setFailed(err instanceof Error ? err.message : "Couldn't create the card."));
    return () => {
      cancelled = true;
    };
  }, [open, key, source, translation, direction, format]);

  // Free each image's URL once it's replaced or the dialog goes away.
  useEffect(() => () => {
    if (rendered) URL.revokeObjectURL(rendered.url);
  }, [rendered]);

  const file = ready ? new File([ready.blob], FILE_NAME, { type: "image/png" }) : null;
  // Only checked once a card exists, which is always after hydration (never on the server).
  const canShareFile = !!file && !!navigator.canShare?.({ files: [file] });
  // Browser-only capability: the server snapshot (false) is also used for the first client
  // render, so the HTML matches and hydration doesn't fail; the real value follows right after.
  const canCopyImage = useSyncExternalStore(
    noopSubscribe,
    () => "ClipboardItem" in window && !!navigator.clipboard?.write,
    () => false
  );

  function flash(kind: "image" | "text") {
    setCopied(kind);
    setTimeout(() => setCopied(null), 1500);
  }

  async function shareImage() {
    if (!file) return;
    try {
      await navigator.share({ files: [file], title: "Understand Kamba translation", text: shareText });
    } catch {
      // Share sheet dismissed -- nothing to do.
    }
  }

  async function copyImage() {
    if (!ready) return;
    try {
      await navigator.clipboard.write([new ClipboardItem({ "image/png": ready.blob })]);
      flash("image");
    } catch {
      onNotice("Couldn't copy the image -- try Download instead.");
    }
  }

  async function copyText() {
    try {
      await navigator.clipboard.writeText(shareText);
      flash("text");
    } catch {
      onNotice("Couldn't copy to clipboard -- your browser may have blocked it.");
    }
  }

  const buttonClass =
    "inline-flex h-12 items-center justify-center gap-2.5 whitespace-nowrap rounded-xl border px-4 text-[15px] font-medium transition sm:px-6 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 disabled:cursor-not-allowed disabled:opacity-50";
  const secondary = `${buttonClass} border-neutral-200 bg-white text-neutral-800 hover:bg-neutral-50`;
  const primary = `${buttonClass} border-butter-300 bg-butter-300 text-neutral-900 hover:bg-butter-400`;

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      onClick={(e) => e.target === dialogRef.current && onClose()} // click on the backdrop
      aria-labelledby="share-card-title"
      aria-describedby="share-card-desc"
      className="m-0 mt-auto max-h-[94dvh] w-full max-w-none overflow-y-auto rounded-t-3xl bg-white p-0 text-neutral-900 shadow-2xl backdrop:bg-neutral-900/50 backdrop:backdrop-blur-[2px] sm:m-auto sm:max-w-xl sm:rounded-3xl"
    >
      <div className="space-y-5 p-5 sm:p-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="share-card-title" className="text-xl font-semibold tracking-tight sm:text-2xl">
              Share this translation
            </h2>
            <p id="share-card-desc" className="mt-1 text-sm text-neutral-500 sm:text-[15px]">
              Copy, download or share your translation.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="-mr-2 -mt-1 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-neutral-500 hover:bg-neutral-100 hover:text-neutral-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500"
          >
            <X className="h-6 w-6" aria-hidden />
          </button>
        </div>

        <div role="radiogroup" aria-label="Card shape" className="grid grid-cols-2 rounded-xl border border-neutral-200 bg-neutral-50 p-1">
          {(Object.keys(CARD_SIZES) as CardFormat[]).map((f) => {
            const active = format === f;
            return (
              <button
                key={f}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => setFormat(f)}
                className={`inline-flex min-h-12 items-center justify-center gap-2 rounded-lg text-[15px] font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-butter-500 ${
                  active ? "bg-butter-300 text-neutral-900" : "text-neutral-500 hover:text-neutral-900"
                }`}
              >
                {active && <AudioLines className="h-4 w-4" aria-hidden />}
                {CARD_SIZES[f].label}
              </button>
            );
          })}
        </div>

        {/* The card's own background is this same cream, so it blends into the panel. */}
        <div className="flex min-h-64 items-center justify-center rounded-2xl bg-[#fefcef] p-2">
          {failed ? (
            <p className="text-sm text-red-600">{failed}</p>
          ) : ready ? (
            // eslint-disable-next-line @next/next/no-img-element -- a local blob: URL, not an optimisable asset
            <img
              src={ready.url}
              alt={`Card showing "${source}" translated as "${translation}"`}
              className="max-h-[50dvh] w-auto rounded-xl"
            />
          ) : (
            <span className="inline-flex items-center gap-2 text-sm text-neutral-500">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              Creating your card…
            </span>
          )}
        </div>

        {/* Phones: a 2x2 grid of equal buttons. Wider: a wrapping row. */}
        <div className="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap">
          {canShareFile && (
            <button type="button" onClick={shareImage} disabled={!ready} className={primary}>
              <Share2 className="h-4 w-4" aria-hidden />
              Share
            </button>
          )}
          {canCopyImage && (
            <button type="button" onClick={copyImage} disabled={!ready} className={canShareFile ? secondary : primary}>
              {copied === "image" ? <Check className="h-4 w-4" aria-hidden /> : <Copy className="h-4 w-4" aria-hidden />}
              {copied === "image" ? "Copied" : "Copy image"}
            </button>
          )}
          <a
            href={ready?.url}
            download={FILE_NAME}
            aria-disabled={!ready}
            onClick={(e) => !ready && e.preventDefault()}
            className={`${!canShareFile && !canCopyImage ? primary : secondary} ${!ready ? "pointer-events-none opacity-50" : ""}`}
          >
            <Download className="h-4 w-4" aria-hidden />
            Download
          </a>
          <button type="button" onClick={copyText} className={secondary}>
            {copied === "text" ? <Check className="h-4 w-4" aria-hidden /> : <Files className="h-4 w-4" aria-hidden />}
            {copied === "text" ? "Copied" : "Copy text"}
          </button>
        </div>
      </div>
    </dialog>
  );
}
