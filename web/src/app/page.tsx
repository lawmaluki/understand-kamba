import StudioCard from "@/components/translator/StudioCard";

export default function Home() {
  return (
    <main className="flex min-h-full flex-1 flex-col bg-gradient-to-b from-butter-100/70 via-neutral-50 to-neutral-50 px-4 pb-24 pt-8 sm:px-6 sm:py-20">
      <div className="mx-auto w-full max-w-5xl">
        <div className="mb-6 max-w-xl sm:mb-10">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-butter-700">
            English &harr; Kikamba
          </p>
          <h1 className="mt-2 text-[2rem] font-medium leading-[1.1] tracking-tight text-neutral-900 sm:mt-3 sm:text-5xl">
            Translate English into Kikamba, then hear it spoken.
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed text-neutral-500 sm:mt-4 sm:text-base">
            Translate in both directions, speak Kikamba to have it transcribed, and listen to
            translations read aloud.
          </p>
        </div>

        <StudioCard />
      </div>
    </main>
  );
}
