"use client";

import { Lock, LockOpen } from "lucide-react";
import { useEffect, useState } from "react";
import { cx } from "@/components/ui";
import { POOLS } from "../content";
import { onFrame, store } from "../motion";
import { Reveal, RevealLines } from "../Reveal";

function Vessel({ pool, accent, filled }: { pool: typeof POOLS.a | typeof POOLS.b; accent: "copper" | "lime"; filled: boolean }) {
  const fill = accent === "copper" ? ["bg-copper", "bg-copper-300", "bg-copper-200"] : ["bg-lime-500", "bg-lime", "bg-lime-200"];
  return (
    <div className="flex flex-col rounded-2xl border border-neutral bg-white p-6 sm:p-8">
      <div className="flex items-center justify-between">
        <span className={cx("rounded-full px-2.5 py-0.5 text-xs font-semibold", accent === "copper" ? "bg-copper-50 text-copper-700 ring-1 ring-inset ring-copper-200" : "bg-lime text-charcoal")}>{pool.tag}</span>
        <span aria-hidden className={cx("h-2 w-2 rounded-full", accent === "copper" ? "bg-copper" : "bg-lime-500")} />
      </div>
      <h3 className="mt-4 font-display text-2xl font-semibold text-charcoal">{pool.title}</h3>
      <p className="mt-2 text-charcoal-soft">{pool.body}</p>
      {/* The vessel: three layers, one per source of money */}
      <div aria-hidden className="relative mt-8 flex h-40 flex-col-reverse overflow-hidden rounded-xl border-2 border-charcoal/80 bg-limestone-50 p-1.5">
        {pool.items.map((_, i) => (
          <div key={i} className={cx("mt-1 rounded-md transition-all duration-1000 ease-out", fill[i])}
            style={{ height: filled ? `${30 - i * 4}%` : "0%", transitionDelay: `${i * 180}ms` }} />
        ))}
      </div>
      <ul className="mt-6 space-y-2 text-sm text-charcoal-soft">
        {pool.items.map((it, i) => (
          <li key={it} className="flex items-center gap-2.5"><span aria-hidden className={cx("h-2.5 w-2.5 rounded-sm", fill[i])} />{it}</li>
        ))}
      </ul>
    </div>
  );
}

// S4 · Two pools, never mixed (limestone, ~120vh). The wall between the pools rises and locks as you scroll in.
export function TwoPools() {
  const [k, setK] = useState(1); // 0..1 wall progress; 1 = locked (also the no-JS / reduced-motion state)
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    return onFrame(() => {
      const p = store.pinned.pools ?? 0;
      const next = Math.round(Math.min(1, Math.max(0, (p - 0.12) / 0.33)) * 20) / 20;
      setK((cur) => (cur === next ? cur : next));
    });
  }, []);
  const locked = k >= 1;

  return (
    <section id="two-pools" data-section="pools" data-theme="light" className="relative scroll-mt-16 bg-limestone py-28 md:min-h-[120vh] md:py-40">
      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <p className="eyebrow">{POOLS.eyebrow}</p>
        <RevealLines as="h2" className="mt-4 max-w-3xl font-display text-3xl font-semibold leading-tight text-charcoal sm:text-5xl"
          lines={["Commercial capital and", "research capital stay apart."]} />
        <div className="mt-14 grid items-stretch gap-6 md:grid-cols-[1fr_auto_1fr]">
          <Reveal><Vessel pool={POOLS.a} accent="copper" filled={k > 0.2} /></Reveal>
          {/* The wall */}
          <div className="flex items-center justify-center md:flex-col" aria-label={locked ? "Pools locked apart" : "Pools separating"}>
            <span className="h-px flex-1 bg-charcoal/20 md:hidden" />
            <div className="relative hidden w-1.5 flex-1 overflow-hidden rounded-full bg-charcoal/10 md:block">
              <div className="absolute inset-x-0 bottom-0 bg-charcoal transition-[height] duration-300" style={{ height: `${k * 100}%` }} />
            </div>
            <span className={cx("mx-3 grid h-11 w-11 shrink-0 place-items-center rounded-full border-2 transition-colors duration-500 md:my-3",
              locked ? "border-charcoal bg-charcoal text-lime" : "border-charcoal/30 bg-white text-charcoal-muted")}>
              {locked ? <Lock className="h-4 w-4" /> : <LockOpen className="h-4 w-4" />}
            </span>
            <span className="h-px flex-1 bg-charcoal/20 md:hidden" />
            <div className="relative hidden w-1.5 flex-1 overflow-hidden rounded-full bg-charcoal/10 md:block">
              <div className="absolute inset-x-0 top-0 bg-charcoal transition-[height] duration-300" style={{ height: `${k * 100}%` }} />
            </div>
          </div>
          <Reveal delay={0.1}><Vessel pool={POOLS.b} accent="lime" filled={k > 0.2} /></Reveal>
        </div>
        <Reveal className="mt-14 grid gap-6 border-t border-charcoal/15 pt-8 md:grid-cols-[1.2fr_1fr]">
          <p className="font-display text-2xl font-semibold leading-snug text-charcoal sm:text-3xl">
            <span className="bg-[linear-gradient(transparent_62%,#D7EB79_62%,#D7EB79_92%,transparent_92%)] [box-decoration-break:clone]">{POOLS.principle}</span>
          </p>
          <p className="text-sm leading-relaxed text-charcoal-muted">{POOLS.note}</p>
        </Reveal>
      </div>
    </section>
  );
}
