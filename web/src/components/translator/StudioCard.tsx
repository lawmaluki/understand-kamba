"use client";

import { useEffect, useRef, useState } from "react";
import { Info } from "lucide-react";
import StudioHeader from "./StudioHeader";
import ContentArea from "./ContentArea";
import DialectSelector from "./DialectSelector";
import FooterControls, { type Rating } from "./FooterControls";
import SavedTranslations from "./SavedTranslations";
import ContributeCta from "@/components/contribute/ContributeCta";
import { getStats, sendFeedback, translateText, type Direction, type Stats } from "@/lib/api";
import { DIALECTS } from "@/lib/dialects";
import { SAMPLE_SENTENCES } from "@/lib/samples";

interface Result {
  direction: Direction;
  source: string;
  translation: string;
  rating: Rating | null;
}

export default function StudioCard() {
  const [direction, setDirection] = useState<Direction>("en_to_kam");
  const [dialectId, setDialectId] = useState(DIALECTS[0].id);
  const [sourceText, setSourceText] = useState(SAMPLE_SENTENCES[0]);
  const [result, setResult] = useState<Result | null>(null);
  const [isTranslating, setIsTranslating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const noticeTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Bumped on every request and direction change, so late responses are dropped.
  const requestId = useRef(0);

  const dialect = DIALECTS.find((d) => d.id === dialectId) ?? DIALECTS[0];

  function showNotice(message: string) {
    setNotice(message);
    if (noticeTimeout.current) clearTimeout(noticeTimeout.current);
    noticeTimeout.current = setTimeout(() => setNotice(null), 4000);
  }

  function refreshStats() {
    getStats()
      .then(setStats)
      .catch(() => {}); // stats are decorative; translate errors surface elsewhere
  }

  useEffect(() => {
    refreshStats();
    return () => {
      if (noticeTimeout.current) clearTimeout(noticeTimeout.current);
    };
  }, []);

  async function handleTranslate(text = sourceText) {
    const trimmed = text.trim();
    if (!trimmed) return;

    const id = ++requestId.current;
    setIsTranslating(true);
    setError(null);
    try {
      const translation = await translateText(trimmed, direction);
      if (id !== requestId.current) return;
      setResult({ direction, source: trimmed, translation, rating: null });
      refreshStats();
      // On phones the result is stacked below the input (and the keyboard may
      // cover it), so bring it into view.
      if (window.matchMedia("(max-width: 767px)").matches) {
        (document.activeElement as HTMLElement | null)?.blur();
        requestAnimationFrame(() =>
          document.getElementById("translation-output")?.scrollIntoView({ behavior: "smooth", block: "start" })
        );
      }
    } catch (err) {
      if (id !== requestId.current) return;
      setError(err instanceof Error ? err.message : "Translation failed.");
    } finally {
      if (id === requestId.current) setIsTranslating(false);
    }
  }

  function handleDirectionChange(next: Direction) {
    requestId.current++;
    setIsTranslating(false);
    setError(null);
    setDirection(next);
    // Swap sides so the last translation carries over, like a phrasebook flip.
    if (result) {
      setSourceText(result.translation);
      setResult({ direction: next, source: result.translation, translation: result.source, rating: null });
    } else {
      setSourceText("");
    }
  }

  async function handleRate(rating: Rating) {
    if (!result || result.rating) return;
    const rated = result;
    setResult({ ...rated, rating });
    try {
      setStats(await sendFeedback({ rating, direction: rated.direction, text: rated.source, translation: rated.translation }));
    } catch (err) {
      setResult((r) => (r === null || r.source !== rated.source ? r : { ...r, rating: null }));
      showNotice(err instanceof Error ? err.message : "Couldn't send your rating.");
    }
  }

  return (
    <div className="w-full">
      {/* Butter frame > cream rim > card, credit line in the bottom edge. */}
      <div className="studio-frame rounded-[26px] px-1.5 pt-1.5 sm:rounded-[30px] sm:px-2 sm:pt-2">
        <div className="rounded-[21px] bg-[#fbfaf5]/90 p-1.5 shadow-[0_1px_2px_rgba(0,0,0,0.04),inset_0_0_0_1px_rgba(255,255,255,0.9)] sm:rounded-[24px] sm:p-2">
          <div className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
            <StudioHeader
              dialectLabel={dialect.label}
              stats={stats}
              direction={direction}
              onDirectionChange={handleDirectionChange}
            />
            <ContentArea
              direction={direction}
              dialectShort={dialect.short}
              sourceText={sourceText}
              onSourceTextChange={setSourceText}
              translatedText={result?.translation ?? ""}
              isTranslating={isTranslating}
              error={error}
              onTranslate={handleTranslate}
              onNotice={showNotice}
            />
            <FooterControls
              direction={direction}
              source={result?.source ?? ""}
              translation={result?.translation ?? ""}
              rating={result?.rating ?? null}
              onRate={handleRate}
              onNotice={showNotice}
            />
          </div>
        </div>
        <p className="py-3 text-center text-sm font-semibold text-neutral-900 sm:py-3.5">
          Powered by Meta NLLB-200
        </p>
      </div>

      {/* Fixed to the bottom of the screen so it's visible wherever you are on the page. */}
      <div
        role="status"
        aria-live="polite"
        className={`fixed inset-x-4 bottom-[max(1rem,env(safe-area-inset-bottom))] z-50 mx-auto flex max-w-md items-center gap-2 rounded-xl bg-neutral-900 px-4 py-3 text-sm text-white shadow-lg transition-all duration-200 ${
          notice ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-2 opacity-0"
        }`}
      >
        <Info className="h-4 w-4 shrink-0" aria-hidden />
        <span>{notice}</span>
      </div>

      <DialectSelector selectedId={dialectId} onSelect={setDialectId} />
      <ContributeCta />
      <SavedTranslations />

      <p className="mt-12 text-xs text-neutral-400">
        Translation by Meta NLLB-200 · Speech recognition by w2v-BERT Kamba (Farmerline) · Voice by
        Meta MMS Swahili
      </p>
    </div>
  );
}
