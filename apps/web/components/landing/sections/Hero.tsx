import { BarChart3, Box, FlaskConical, Layers, Leaf, Zap, type LucideIcon } from "lucide-react";
import { DEMO_BADGE, DEMO_KPIS } from "@/lib/uplo-demo-data";
import { Button } from "@/components/ui";
import { HERO } from "../content";
import { RingSvg } from "../RingSvg";

const STATS: { icon: LucideIcon; value: string; label: string }[] = [
  { icon: Layers, value: `$${DEMO_KPIS.verifiedAssets.value / 1e6}M`, label: "Verified commercial assets" },
  { icon: FlaskConical, value: String(DEMO_KPIS.researchProjects.value), label: "Research projects" },
  { icon: BarChart3, value: `$${DEMO_KPIS.innovationCapital.value / 1e3}K`, label: "Innovation capital allocated" },
];

const PILLAR_ICON: Record<string, LucideIcon> = { circular: Leaf, industrial: Box, innovation: Zap, solutions: Layers };

// S1 · Hero (limestone, pinned ~150vh). The headline is plain server-rendered text - visible on first paint,
// never waiting for WebGL. `data-ring-slot` marks where the 3D ring sits; the SVG twin fills it when there is
// no 3D (mobile, reduced motion, no WebGL) and is hidden once the canvas is live.
export function Hero() {
  return (
    <section data-section="hero" data-theme="light" className="relative bg-limestone md:h-[150vh]">
      <div className="relative flex min-h-[100svh] flex-col md:sticky md:top-[61px] md:h-[calc(100vh-61px)] md:min-h-0">
        <div className="relative z-10 mx-auto grid w-full max-w-7xl flex-1 content-start items-center gap-8 px-4 pt-12 sm:px-6 md:grid-cols-12 md:content-center md:pt-6 lg:px-8">
          <div className="md:col-span-7 lg:col-span-6">
            <p className="eyebrow flex items-center gap-2"><span aria-hidden className="h-1.5 w-1.5 rounded-full bg-lime-500" />{HERO.eyebrow}</p>
            <h1 className="mt-4 font-display text-[clamp(2.75rem,5.6vw,4.25rem)] font-semibold leading-[1.02] tracking-tight text-charcoal">
              <span className="block">{HERO.line1}</span>
              <span className="mt-1 block text-lime-650">{HERO.line2}</span>
            </h1>
            <p className="hero-sub mt-5 max-w-md text-lg leading-relaxed text-charcoal-soft">{HERO.sub}</p>
            <div className="hero-cta mt-7 flex flex-wrap gap-3">
              <Button href="/raise" arrow className="px-5 py-3">Explore Opportunities</Button>
              <Button href="#capital-flow" variant="secondary" className="px-5 py-3">How It Works</Button>
            </div>
            {/* Brand pillars, as on the board's brand overview */}
            <ul className="mt-8 grid max-w-xl grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
              {HERO.pillars.map((p) => {
                const Icon = PILLAR_ICON[p.id];
                return (
                  <li key={p.id} className="flex items-center gap-2.5">
                    <Icon aria-hidden className="h-5 w-5 shrink-0 text-charcoal" strokeWidth={1.5} />
                    <span className="text-[10px] font-semibold uppercase leading-tight tracking-[0.14em] text-charcoal">{p.label}</span>
                  </li>
                );
              })}
            </ul>
          </div>

          {/* Ring slot: the 3D ring is drawn here by the fixed canvas; the SVG is the fallback. */}
          <div data-ring-slot className="relative mx-auto aspect-square w-[min(78vw,26rem)] md:col-span-5 md:w-full lg:col-span-6 lg:max-w-[min(30rem,62vh)]">
            <div className="ring-fallback absolute inset-0 grid place-items-center">
              <div aria-hidden className="absolute inset-[6%] rounded-[2rem] bg-[radial-gradient(120%_90%_at_30%_20%,#d9d4c8_0%,#b9b3a6_45%,#8f8a80_100%)] shadow-[inset_0_-30px_60px_rgba(30,35,32,0.25)]" />
              <RingSvg lit={1} className="relative w-[68%]" title="UPLO capital ring - one segment lit" />
            </div>
          </div>
        </div>

        {/* Vertical caption, as on the brand board */}
        <p aria-hidden className="pointer-events-none absolute right-6 top-1/2 z-10 hidden -translate-y-1/2 text-right font-display text-xs font-semibold uppercase leading-relaxed tracking-eyebrow text-charcoal xl:block">
          {HERO.caption.map((l) => <span key={l} className="block">{l}</span>)}
        </p>

        {/* Stat row, as on the board's landing mock-up. Simulated figures, labelled as such. */}
        <div className="relative z-10 mx-auto w-full max-w-7xl px-4 pb-6 pt-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center gap-x-10 gap-y-4 border-t border-charcoal/15 pt-5">
            {STATS.map(({ icon: Icon, value, label }) => (
              <div key={label} className="flex items-center gap-3">
                <Icon aria-hidden className="h-7 w-7 shrink-0 text-charcoal" strokeWidth={1.4} />
                <div>
                  <p className="figure text-2xl font-semibold leading-none text-charcoal">{value}</p>
                  <p className="mt-1 text-xs text-charcoal-muted">{label}</p>
                </div>
              </div>
            ))}
            <span className="ml-auto text-[11px] font-medium text-charcoal-muted">{DEMO_BADGE}</span>
          </div>
        </div>
      </div>
    </section>
  );
}
