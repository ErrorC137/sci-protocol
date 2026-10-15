"use client";

import { useEffect, useRef, useState } from "react";
import { cx } from "@/components/ui";
import { GAP, ILLUSTRATIVE } from "../content";
import { Reveal, RevealLines } from "../Reveal";
import { RingSvg } from "../RingSvg";

// The 90-day timer ticks while the card is on screen (and sits at day 90 for reduced motion / no JS).
function InvoiceCard() {
  const ref = useRef<HTMLDivElement>(null);
  const [day, setDay] = useState(90);
  useEffect(() => {
    const el = ref.current;
    if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let timer = 0;
    const io = new IntersectionObserver(([e]) => {
      window.clearInterval(timer);
      if (!e.isIntersecting) return;
      setDay(0);
      timer = window.setInterval(() => setDay((d) => (d >= 90 ? 0 : d + 1)), 70);
    }, { threshold: 0.4 });
    io.observe(el);
    return () => { io.disconnect(); window.clearInterval(timer); };
  }, []);
  return (
    <div ref={ref} className="rounded-xl border border-charcoal-700 bg-charcoal-800 p-5 font-sans">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] uppercase tracking-[0.14em] text-limestone-400">Invoice · INV-0142</p>
          <p className="figure mt-1 text-3xl font-semibold text-limestone-50">$100,000</p>
          <p className="mt-1 text-xs text-limestone-400">Recovered lithium carbonate · Net 90</p>
        </div>
        <span className="rounded-full border border-copper/60 px-2 py-0.5 text-[11px] font-semibold text-copper-200">Awaiting payment</span>
      </div>
      <div className="mt-5">
        <div className="flex justify-between text-xs text-limestone-400">
          <span>Day <span className="figure text-limestone-50">{day}</span> of 90</span>
          <span>{90 - day} days of working capital locked</span>
        </div>
        <div className="mt-2 h-1.5 rounded-full bg-charcoal-600">
          <div className="h-1.5 rounded-full bg-copper transition-[width] duration-75" style={{ width: `${(day / 90) * 100}%` }} />
        </div>
      </div>
    </div>
  );
}

function TrlBar() {
  return (
    <div className="rounded-xl border border-charcoal-700 bg-charcoal-800 p-5">
      <p className="text-[11px] uppercase tracking-[0.14em] text-limestone-400">Technology readiness level</p>
      <ol className="mt-4 grid grid-cols-9 gap-1.5" aria-label="TRL 1 to 9; 4 to 6 is the funding gap">
        {Array.from({ length: 9 }, (_, i) => {
          const n = i + 1, gap = n >= 4 && n <= 6;
          return (
            <li key={n} className={cx("flex h-14 flex-col items-center justify-end rounded-md pb-1.5 text-xs font-semibold",
              gap ? "gap-glow bg-lime/15 text-lime ring-1 ring-inset ring-lime/60" : n >= 7 ? "bg-sage/25 text-limestone-100" : "bg-charcoal-600 text-limestone-300")}>
              {n}
            </li>
          );
        })}
      </ol>
      <div className="mt-3 grid grid-cols-9 text-[11px] text-limestone-400">
        <span className="col-span-3">Lab</span>
        <span className="col-span-3 text-center font-semibold text-lime">The gap</span>
        <span className="col-span-3 text-right">Commercial</span>
      </div>
    </div>
  );
}

// S2 · The gap (charcoal, ~120vh).
export function Gap() {
  return (
    <section data-section="gap" data-theme="dark" className="relative overflow-hidden bg-charcoal py-28 text-limestone-50 md:min-h-[120vh] md:py-40">
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-1/2 h-px bg-gradient-to-r from-transparent via-copper/50 to-transparent" />
      <div aria-hidden className="pointer-events-none absolute inset-y-0 left-1/2 hidden w-px bg-gradient-to-b from-transparent via-copper/40 to-transparent md:block" />
      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-start justify-between gap-6">
          <p className="eyebrow text-limestone-400">{GAP.eyebrow}</p>
          {/* Ring slot: the ring arrives here dark - nothing is lit yet. */}
          <div data-ring-slot className="relative -mt-6 hidden aspect-square w-40 md:block">
            <div className="ring-fallback absolute inset-0"><RingSvg tone="dark" lit={0} className="w-full" /></div>
          </div>
        </div>
        <div className="mt-4 grid gap-16 md:grid-cols-2 md:gap-20">
          <div className="space-y-6">
            <RevealLines as="h2" className="font-display text-3xl font-semibold leading-tight sm:text-4xl" lines={["Recyclers wait", "90 days to get paid."]} />
            <Reveal><p className="max-w-md text-limestone-300">{GAP.left.body}</p></Reveal>
            <Reveal delay={0.1}><InvoiceCard /></Reveal>
          </div>
          <div className="space-y-6">
            <RevealLines as="h2" className="font-display text-3xl font-semibold leading-tight sm:text-4xl" lines={["Upcycling research", "stalls at TRL 4–6."]} />
            <Reveal><p className="max-w-md text-limestone-300">{GAP.right.body}</p></Reveal>
            <Reveal delay={0.1}><TrlBar /></Reveal>
          </div>
        </div>
        <Reveal className="mt-20 flex flex-wrap items-baseline justify-between gap-4 border-t border-charcoal-700 pt-8">
          <p className="font-display text-2xl font-semibold text-lime sm:text-3xl">{GAP.bridge}</p>
          <p className="text-xs text-limestone-400">Figures on this page: {ILLUSTRATIVE.toLowerCase()}.</p>
        </Reveal>
      </div>
    </section>
  );
}
