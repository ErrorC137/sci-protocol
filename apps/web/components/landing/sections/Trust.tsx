import { Landmark, ScanSearch, ShieldCheck, type LucideIcon } from "lucide-react";
import { TRUST } from "../content";
import { Reveal, RevealLines } from "../Reveal";

const ICON: Record<string, LucideIcon> = { escrow: Landmark, transparency: ScanSearch, privacy: ShieldCheck };

// S7 · Built to be trusted (charcoal). Only mechanics that exist in this codebase, plus the honest scope line.
export function Trust() {
  return (
    <section id="trust" data-section="trust" data-theme="dark" className="relative scroll-mt-16 bg-charcoal py-28 text-limestone-50 md:min-h-screen md:py-40">
      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <p className="eyebrow text-limestone-400">{TRUST.eyebrow}</p>
        <RevealLines as="h2" className="mt-4 max-w-3xl font-display text-3xl font-semibold leading-tight sm:text-5xl" lines={[TRUST.title]} />
        <div className="mt-16 grid gap-px overflow-hidden rounded-2xl border border-charcoal-700 bg-charcoal-700 md:grid-cols-3">
          {TRUST.points.map((p, i) => {
            const Icon = ICON[p.id];
            return (
              <Reveal key={p.id} delay={i * 0.1} className="bg-charcoal p-7">
                <span className="grid h-11 w-11 place-items-center rounded-full border border-lime/40 text-lime"><Icon aria-hidden className="h-5 w-5" strokeWidth={1.5} /></span>
                <h3 className="mt-6 font-display text-xl font-semibold">{p.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-limestone-300">{p.body}</p>
              </Reveal>
            );
          })}
        </div>
        <Reveal className="mt-10 flex items-center gap-3 text-sm text-limestone-300">
          <span aria-hidden className="h-2 w-2 rounded-full bg-copper" />{TRUST.scope}
        </Reveal>
      </div>
    </section>
  );
}
