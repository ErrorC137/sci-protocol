import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { SiteFooter, SiteNav } from "@/components/SiteChrome";
import { Button, PrivacyBanner } from "@/components/ui";

// Interim home (Phase 2: same content as before, UPLO styling). Phase 3 replaces it with the cinematic landing.
const STEPS = [
  { n: "01", title: "Describe your work once", body: "Categories and stage only - never method, composition or data.", href: "/profile", cta: "Start the profile" },
  { n: "02", title: "Get matched", body: "Hard eligibility rules first, then hybrid ranking, then plain-language reasons.", href: "/matches", cta: "See matches" },
  { n: "03", title: "Pre-filled applications", body: "Forms filled from your profile, every field flagged green / amber / red for your review.", href: "/discover", cta: "Browse funders" },
  { n: "04", title: "Milestone-gated raise", body: "For work too early for grants: no progress, no money - and missed milestones refund funders.", href: "/raise", cta: "Open a raise" },
];

export default function Home() {
  return (
    <>
      <SiteNav />
      <main>
        <section className="mx-auto grid max-w-7xl gap-10 px-4 pb-16 pt-14 sm:px-6 lg:grid-cols-[1.25fr_1fr] lg:items-center lg:px-8 lg:pt-20">
          <div>
            <p className="eyebrow flex items-center gap-2"><span aria-hidden className="h-1.5 w-1.5 rounded-full bg-lime-500" />UPLO</p>
            <h1 className="mt-3 text-4xl font-semibold leading-[1.05] tracking-tight text-charcoal sm:text-5xl lg:text-6xl">
              Find every grant you’re eligible for - <span className="bg-[linear-gradient(transparent_62%,#D7EB79_62%,#D7EB79_92%,transparent_92%)] [box-decoration-break:clone]">without disclosing your invention.</span>
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-charcoal-soft">
              Describe your research once, in non-confidential terms. Get matched to grants, accelerators and crowdfunding
              routes across Thailand, Southeast Asia and beyond, with the paperwork pre-filled - and milestone-gated
              on-chain funding for the projects traditional grants won’t reach.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button href="/profile" arrow>Describe your project</Button>
              <Button href="/discover" variant="secondary">Browse opportunities</Button>
            </div>
          </div>
          <div className="rounded-2xl bg-charcoal p-6 text-limestone-100 sm:p-8">
            <p className="eyebrow text-limestone-400">Why this exists</p>
            <ul className="mt-5 divide-y divide-charcoal-700 text-sm leading-relaxed">
              <li className="pb-4"><strong className="figure block text-3xl font-semibold text-lime">20-30</strong>IPs ever licensed or commercialised at one Thai university IP institute, out of hundreds to thousands filed (TUIPI, team interview).</li>
              <li className="py-4"><strong className="figure block text-3xl font-semibold text-lime">~10 in 100</strong>Thai grant applications succeed - each one a multi-week manual document exercise.</li>
              <li className="py-4">A senior national-agency researcher told us she has commercialisation-ready patents she doesn’t advance <em>purely</em> for lack of lab-to-industry funding.</li>
              <li className="pt-4">Researchers won’t upload their work to get matched - they fear idea theft. So we never ask.</li>
            </ul>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8"><PrivacyBanner /></section>

        <section id="how-it-works" className="mx-auto max-w-7xl scroll-mt-20 px-4 py-16 sm:px-6 lg:px-8">
          <p className="eyebrow">How it works</p>
          <div className="mt-6 grid gap-px overflow-hidden rounded-xl border border-neutral bg-neutral sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s) => (
              <div key={s.n} className="flex flex-col bg-white p-6">
                <span className="figure text-sm font-semibold text-copper-700">{s.n}</span>
                <h2 className="mt-3 text-lg font-semibold text-charcoal">{s.title}</h2>
                <p className="mt-2 flex-1 text-sm leading-relaxed text-charcoal-soft">{s.body}</p>
                <Link href={s.href} className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-charcoal hover:gap-2.5 transition-all">
                  {s.cta} <ArrowRight aria-hidden className="h-4 w-4" />
                </Link>
              </div>
            ))}
          </div>
        </section>

        <section id="about" className="mx-auto max-w-7xl scroll-mt-20 px-4 pb-20 sm:px-6 lg:px-8">
          <div className="rounded-xl border border-neutral bg-white p-6 text-sm text-charcoal-soft sm:p-8">
            <p className="font-display text-lg font-semibold text-charcoal">Where this demo ends (on purpose)</p>
            <ul className="mt-4 grid gap-3 sm:grid-cols-2">
              <li className="flex gap-3"><span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-copper" /><span>On-chain funding runs on <strong className="text-charcoal">testnet only</strong> with a mock stablecoin - no real value moves.</span></li>
              <li className="flex gap-3"><span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-copper" /><span>Fractional tokens demonstrate a mechanism. Claims on future revenue are very likely securities; a real deployment needs counsel. Nothing here is an offering.</span></li>
              <li className="flex gap-3"><span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-copper" /><span>The milestone attestor is centralized (our backend signer). Decentralizing it is future work.</span></li>
              <li className="flex gap-3"><span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-copper" /><span>Vault proofs are timestamped existence proofs - not prior art, not a patent filing, not IP registration.</span></li>
              <li className="flex gap-3"><span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-copper" /><span>Applications are never submitted for you. Every field goes through your review.</span></li>
            </ul>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
