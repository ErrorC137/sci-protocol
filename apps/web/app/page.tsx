import Link from "next/link";
import { Button, Card, PrivacyBanner } from "@/components/ui";

const STEPS = [
  { n: 1, title: "Describe your work once", body: "Categories and stage only - never method, composition or data.", href: "/profile", cta: "Start the profile" },
  { n: 2, title: "Get matched", body: "Hard eligibility rules first, then hybrid ranking, then plain-language reasons.", href: "/matches", cta: "See matches" },
  { n: 3, title: "Pre-filled applications", body: "Forms filled from your profile, every field flagged green / amber / red for your review.", href: "/discover", cta: "Browse funders" },
  { n: 4, title: "Milestone-gated raise", body: "For work too early for grants: no progress, no money - and missed milestones refund funders.", href: "/raise", cta: "Open a raise" },
];

export default function Home() {
  return (
    <div className="space-y-10">
      <section className="grid gap-8 pt-6 lg:grid-cols-[1.3fr_1fr] lg:items-center">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wider text-brand-600">SCI Protocol</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink sm:text-5xl">
            Find every grant you’re eligible for - without disclosing your invention.
          </h1>
          <p className="mt-4 max-w-2xl text-lg text-ink-soft">
            Describe your research once, in non-confidential terms. Get matched to grants, accelerators and crowdfunding
            routes across Thailand, Southeast Asia and beyond, with the paperwork pre-filled - and milestone-gated
            on-chain funding for the projects traditional grants won’t reach.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button href="/profile">Describe your project</Button>
            <Button href="/discover" variant="secondary">Browse opportunities</Button>
          </div>
        </div>
        <Card className="space-y-4">
          <p className="text-sm font-semibold text-ink">Why this exists</p>
          <ul className="space-y-3 text-sm text-ink-soft">
            <li><strong className="text-ink">20-30</strong> IPs ever licensed or commercialised at one Thai university IP institute, out of hundreds to thousands filed (TUIPI, team interview).</li>
            <li><strong className="text-ink">~10 in 100</strong> Thai grant applications succeed - each one a multi-week manual document exercise.</li>
            <li>A senior national-agency researcher told us she has commercialisation-ready patents she doesn’t advance <em>purely</em> for lack of lab-to-industry funding.</li>
            <li>Researchers won’t upload their work to get matched - they fear idea theft. So we never ask.</li>
          </ul>
        </Card>
      </section>

      <PrivacyBanner />

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((s) => (
          <Card key={s.n} className="flex flex-col">
            <span className="grid h-8 w-8 place-items-center rounded-full bg-brand-100 text-sm font-bold text-brand-700">{s.n}</span>
            <h2 className="mt-3 font-semibold text-ink">{s.title}</h2>
            <p className="mt-1 flex-1 text-sm text-ink-soft">{s.body}</p>
            <Link href={s.href} className="mt-4 text-sm font-semibold text-brand-700 hover:underline">{s.cta} →</Link>
          </Card>
        ))}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-ink-soft">
        <p className="font-semibold text-ink">Where this demo ends (on purpose)</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>On-chain funding runs on <strong>testnet only</strong> with a mock stablecoin - no real value moves.</li>
          <li>Fractional tokens demonstrate a mechanism. Claims on future revenue are very likely securities; a real deployment needs counsel. Nothing here is an offering.</li>
          <li>The milestone attestor is centralized (our backend signer). Decentralizing it is future work.</li>
          <li>Vault proofs are timestamped existence proofs - not prior art, not a patent filing, not IP registration.</li>
          <li>Applications are never submitted for you. Every field goes through your review.</li>
        </ul>
      </section>
    </div>
  );
}
