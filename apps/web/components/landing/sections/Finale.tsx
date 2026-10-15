import { Button } from "@/components/ui";
import { FINALE } from "../content";
import { RevealLines } from "../Reveal";
import { RingSvg } from "../RingSvg";

// S8 · Finale (limestone). The complete, glowing ring settles behind the headline (3D, or the SVG twin), then a
// marquee strip in charcoal leads into the footer.
export function Finale() {
  const items = [...FINALE.marquee, ...FINALE.marquee];
  return (
    <section data-section="finale" data-theme="light" className="relative overflow-hidden bg-limestone">
      <div className="relative mx-auto flex min-h-[100svh] max-w-7xl flex-col items-center justify-center px-4 py-28 text-center sm:px-6 lg:px-8">
        <div data-ring-slot className="pointer-events-none absolute left-1/2 top-1/2 aspect-square w-[min(92vw,44rem)] -translate-x-1/2 -translate-y-1/2">
          <div className="ring-fallback absolute inset-0 grid place-items-center opacity-25">
            <RingSvg lit={6} glow className="w-full" />
          </div>
        </div>
        <div className="relative z-10">
          <RevealLines as="h2" className="font-display text-[clamp(2.4rem,6vw,4.75rem)] font-semibold leading-[1.04] tracking-tight text-charcoal"
            lines={[FINALE.title1, <span key="2" className="bg-charcoal px-3 text-lime [box-decoration-break:clone]">{FINALE.title2}</span>]} />
          <div className="mt-10 flex flex-wrap justify-center gap-3">
            <Button href="/raise" arrow className="px-5 py-3">Explore Opportunities</Button>
            <Button href="#two-pools" variant="secondary" className="px-5 py-3">For Investors</Button>
            <Button href="/profile" variant="secondary" className="px-5 py-3">For Innovators</Button>
          </div>
        </div>
      </div>
      <div className="relative z-10 overflow-hidden border-y border-charcoal bg-charcoal py-4" aria-label={FINALE.marquee.join(" × ")}>
        <div aria-hidden className="marquee flex w-max gap-8 whitespace-nowrap font-display text-sm font-semibold uppercase tracking-eyebrow text-limestone-100">
          {items.map((m, i) => (
            <span key={i} className="flex items-center gap-8">{m}<span className="text-lime">×</span></span>
          ))}
        </div>
      </div>
    </section>
  );
}
