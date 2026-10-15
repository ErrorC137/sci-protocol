import { REVENUE } from "../content";
import { Reveal, RevealLines } from "../Reveal";

// S5 · Three revenue streams (charcoal, ~100vh). Cards hang off a horizon axis; tier prices are market-test
// proposals and are labelled as such.
export function Revenue() {
  return (
    <section data-section="revenue" data-theme="dark" className="relative bg-charcoal py-28 text-limestone-50 md:min-h-screen md:py-40">
      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <p className="eyebrow text-limestone-400">{REVENUE.eyebrow}</p>
        <RevealLines as="h2" className="mt-4 font-display text-3xl font-semibold leading-tight sm:text-5xl" lines={[REVENUE.title]} />

        {/* Horizon axis */}
        <div aria-hidden className="relative mt-16 hidden h-px bg-gradient-to-r from-copper via-sage to-lime md:block">
          {[0, 50, 100].map((x) => (
            <span key={x} className="absolute -top-1.5 h-3 w-3 -translate-x-1/2 rounded-full border-2 border-charcoal bg-limestone-50" style={{ left: `${x === 0 ? 16.6 : x === 50 ? 50 : 83.3}%` }} />
          ))}
        </div>

        <ol className="mt-10 grid gap-6 md:grid-cols-3">
          {REVENUE.streams.map((s, i) => (
            <Reveal as="li" key={s.title} delay={i * 0.12}
              className="flex flex-col rounded-2xl border border-charcoal-700 bg-charcoal-800 p-6">
              <p className="text-[11px] font-semibold uppercase tracking-eyebrow text-lime">{s.horizon}</p>
              <h3 className="mt-3 font-display text-xl font-semibold">{s.title}</h3>
              <p className="mt-1 text-xs text-limestone-400">Paid by: {s.payer}</p>
              <p className="mt-4 text-sm leading-relaxed text-limestone-300">{s.body}</p>
              {"tiers" in s && (
                <div className="mt-5 rounded-xl border border-charcoal-600 p-4">
                  <ul className="space-y-2 text-sm">
                    {s.tiers.map((t) => (
                      <li key={t.name} className="flex justify-between gap-3">
                        <span className="text-limestone-100">{t.name}</span><span className="figure text-limestone-300">{t.price}</span>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-3 inline-flex rounded-full bg-copper/20 px-2 py-0.5 text-[11px] font-semibold text-copper-200">{s.tiersNote}</p>
                </div>
              )}
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}
