"use client";

import { ArrowRight, BatteryFull, FlaskConical } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { StatusChip, cx } from "@/components/ui";
import { FLOW, FLOW_CLOSE, ILLUSTRATIVE, WATERFALL } from "../content";
import { onFrame, store } from "../motion";
import { Counter } from "../Reveal";
import { RingSvg } from "../RingSvg";
import { useMedia } from "../useMedia";

const PHASES = FLOW.length + 1; // five stations, then the loop closes

const usd = (n: number) => `$${n.toLocaleString("en-US")}`;

// Small explanatory visual per station. `on` is true while the station is the active one (drives counters).
function StationVisual({ id, on }: { id: string; on: boolean }) {
  const W = WATERFALL;
  switch (id) {
    case "assets":
      return (
        <div className="flex items-end gap-2" aria-hidden>
          {Array.from({ length: 6 }, (_, i) => (
            <span key={i} className={cx("flex h-14 w-7 flex-col justify-end overflow-hidden rounded-md border transition-all duration-700",
              on ? "border-copper/60 bg-copper/15" : "border-charcoal-600 bg-charcoal-800")} style={{ transitionDelay: `${i * 60}ms` }}>
              <span className="block bg-copper/70 transition-all duration-700" style={{ height: on ? `${40 + ((i * 37) % 50)}%` : "0%", transitionDelay: `${i * 60}ms` }} />
            </span>
          ))}
          <BatteryFull className="ml-2 h-6 w-6 text-copper-200" strokeWidth={1.5} />
        </div>
      );
    case "financing":
      return (
        <div className="space-y-3">
          <div className="flex items-center justify-between rounded-lg border border-charcoal-600 bg-charcoal-800 px-4 py-3">
            <span className="text-sm text-limestone-300">Invoice INV-0142 · {usd(W.invoice)}</span>
            {on ? <StatusChip status="verified">VERIFIED</StatusChip> : <StatusChip status="progress">Pending</StatusChip>}
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-limestone-400">Pool A</span>
            <span className="relative h-px flex-1 overflow-hidden bg-charcoal-600">
              <span className={cx("absolute inset-y-0 left-0 w-full origin-left bg-lime transition-transform duration-1000", on ? "scale-x-100" : "scale-x-0")} />
            </span>
            <span className="figure font-semibold text-lime"><Counter value={W.advance} prefix="$" run={on} /></span>
            <ArrowRight aria-hidden className="h-4 w-4 text-lime" />
            <span className="text-limestone-300">Recycler, today</span>
          </div>
        </div>
      );
    case "revenue":
      return (
        <div className="space-y-2">
          <div className="flex h-3 overflow-hidden rounded-full bg-charcoal-600">
            <span className="bg-sage/70 transition-all duration-1000" style={{ width: on ? "98%" : "0%" }} />
            <span className="bg-lime transition-all delay-500 duration-700" style={{ width: on ? "2%" : "0%" }} />
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-limestone-300">To the financing provider <span className="figure ml-1 text-limestone-50"><Counter value={W.toFinancier} prefix="$" run={on} /></span></span>
            <span className="text-lime">Platform fee <span className="figure ml-1 font-semibold"><Counter value={W.platformFee} prefix="$" run={on} /></span></span>
          </div>
        </div>
      );
    case "innovation":
      return (
        <dl className="grid grid-cols-[1fr_auto] gap-x-6 gap-y-1.5 text-sm">
          <dt className="text-limestone-400">Platform revenue</dt><dd className="figure text-right text-limestone-100">{usd(W.platformFee)}</dd>
          <dt className="text-limestone-400">Direct costs</dt><dd className="figure text-right text-limestone-100">−{usd(W.directCosts)}</dd>
          <dt className="border-t border-charcoal-600 pt-1.5 text-limestone-300">Gross contribution</dt><dd className="figure border-t border-charcoal-600 pt-1.5 text-right text-limestone-50">{usd(W.grossContribution)}</dd>
          <dt className="font-semibold text-lime">20% → Innovation Treasury (Pool B)</dt><dd className="figure text-right font-semibold text-lime"><Counter value={W.treasury} prefix="$" run={on} /></dd>
          <dt className="text-limestone-400">Remains with the business</dt><dd className="figure text-right text-limestone-300">{usd(W.retained)}</dd>
        </dl>
      );
    case "research":
      return (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <FlaskConical aria-hidden className="h-6 w-6 text-lime" strokeWidth={1.5} />
            <ol className="grid flex-1 grid-cols-9 gap-1" aria-label="TRL progress from 4 to 6">
              {Array.from({ length: 9 }, (_, i) => {
                const n = i + 1, reached = on ? n <= 6 : n <= 4;
                return (
                  <li key={n} className={cx("grid h-8 place-items-center rounded text-[11px] font-semibold transition-colors duration-500",
                    reached ? (n >= 4 ? "bg-lime text-charcoal" : "bg-charcoal-600 text-limestone-300") : "bg-charcoal-800 text-limestone-400 ring-1 ring-inset ring-charcoal-600")}
                    style={{ transitionDelay: on ? `${Math.max(0, n - 4) * 350}ms` : "0ms" }}>{n}</li>
                );
              })}
            </ol>
          </div>
          <p className="text-sm text-limestone-300">Each milestone is paid only after evidence is approved. Miss a deadline and backers are refunded.</p>
        </div>
      );
    default:
      return null;
  }
}

function Panel({ n, title, children, on }: { n: string; title: string; children: ReactNode; on: boolean }) {
  return (
    <div data-active={on} className={cx("flow-panel transition-[opacity,transform] duration-700 ease-out",
      "md:absolute md:inset-0 md:flex md:flex-col md:justify-center",
      on ? "md:translate-y-0 md:opacity-100" : "md:pointer-events-none md:translate-y-6 md:opacity-0")}>
      <p className="figure text-sm font-semibold text-copper-200">{n}</p>
      <h3 className="mt-2 font-display text-3xl font-semibold leading-tight text-limestone-50 sm:text-4xl">{title}</h3>
      <div className="mt-5 space-y-6">{children}</div>
    </div>
  );
}

// S3 · The Capital Flow (charcoal, pinned ~430vh). Desktop: sticky stage, one station at a time; the ring (3D,
// or the SVG twin) lights one segment per station. Mobile: the same panels stacked, each with its own 2D ring.
export function CapitalFlow() {
  const [phase, setPhase] = useState(0);
  useEffect(() => onFrame(() => {
    const p = store.pinned.flow ?? 0;
    const next = Math.min(PHASES - 1, Math.floor(p * PHASES * 0.999));
    setPhase((cur) => (cur === next ? cur : next));
  }), []);
  const closed = phase === PHASES - 1;
  // Mobile shows every station stacked, so each visual is simply in its finished state.
  const desktop = useMedia("(min-width: 768px)", true);

  return (
    <section id="capital-flow" data-section="flow" data-theme="dark" className="relative scroll-mt-0 bg-charcoal text-limestone-50 md:h-[430vh]">
      <div className="md:sticky md:top-0 md:flex md:h-screen md:items-center">
        <div className="relative z-10 mx-auto grid w-full max-w-7xl gap-12 px-4 py-24 sm:px-6 md:grid-cols-12 md:py-0 lg:px-8">
          {/* Step indicator */}
          <ol aria-hidden className="hidden flex-col justify-center gap-3 md:col-span-1 md:flex">
            {FLOW.map((s, i) => (
              <li key={s.n} className={cx("figure text-xs font-semibold transition-colors duration-500", i === phase ? "text-lime" : i < phase || closed ? "text-limestone-300" : "text-charcoal-600")}>
                {s.n}<span className={cx("mt-1 block h-px bg-current transition-all duration-500", i === phase ? "w-8" : "w-3")} />
              </li>
            ))}
          </ol>

          <div className="md:col-span-5">
            <p className="eyebrow text-limestone-400">The capital flow</p>
            <p className="mt-2 text-xs text-limestone-400">{ILLUSTRATIVE}</p>
            <div className="relative mt-8 space-y-16 md:h-[26rem] md:space-y-0">
              {FLOW.map((s, i) => (
                <div key={s.id} className="grid gap-6 md:contents">
                  <RingSvg tone="dark" lit={i + 1} className="w-24 md:hidden" title={`Stage ${i + 1} of 5 lit`} />
                  <Panel n={s.n} title={s.title} on={desktop ? i === phase : true}>
                    <p className="max-w-md text-lg leading-relaxed text-limestone-300">{s.body}</p>
                    <StationVisual id={s.id} on={!desktop || i <= phase} />
                  </Panel>
                </div>
              ))}
              <div className="grid gap-6 md:contents">
                <RingSvg tone="dark" lit={6} glow className="w-24 md:hidden" title="Loop closed - all segments lit" />
                <Panel n="↻" title={FLOW_CLOSE.title} on={desktop ? closed : true}>
                  <p className="max-w-md text-lg leading-relaxed text-limestone-300">{FLOW_CLOSE.body}</p>
                  <p className="font-display text-2xl font-semibold text-lime">{FLOW_CLOSE.tagline}</p>
                </Panel>
              </div>
            </div>
          </div>

          {/* Ring slot (desktop): 3D ring orbits here; SVG twin as fallback */}
          <div data-ring-slot className="relative hidden aspect-square w-full max-w-[34rem] self-center justify-self-center md:col-span-6 md:block">
            <div className="ring-fallback absolute inset-0 grid place-items-center">
              <RingSvg tone="dark" lit={closed ? 6 : phase + 1} glow={closed} className="w-[78%]" title={`Capital flow ring: ${closed ? "complete" : `stage ${phase + 1} of 5`}`} />
              <p className="absolute bottom-0 text-center text-xs uppercase tracking-eyebrow text-limestone-400">
                {closed ? "Loop closed" : `${FLOW[phase].n} · ${FLOW[phase].title}`}
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
