import { sectorPath } from "./RingSvg";

// S0 · Preloader - pure CSS so it plays from the very first frame, before (and regardless of) hydration.
// In the server HTML but `display: none` unless the inline gate put `preload` on <html> (motion allowed, first visit
// this session). The ring draws segment by segment while a counter runs 00 -> 100 (CSS @property), the lime segment
// lands, then the overlay fades out at ~0.95s. Landing removes the class and remembers the visit.
export function Preloader() {
  return (
    <div aria-hidden className="preloader fixed inset-0 z-[60] place-items-center bg-limestone">
      <div className="pl-inner flex flex-col items-center gap-6">
        <svg viewBox="0 0 200 200" className="w-28 overflow-visible">
          {Array.from({ length: 6 }, (_, i) => (
            <path key={i} d={sectorPath(i, 6)} className={i === 0 ? "pl-seg pl-seg-lime" : "pl-seg"} style={{ animationDelay: `${80 + i * 120}ms` }} />
          ))}
        </svg>
        <span className="pl-count font-display text-sm font-semibold tabular-nums tracking-[0.2em] text-charcoal" />
      </div>
    </div>
  );
}
