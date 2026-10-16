// Every word and number on the landing page, in one place. Figures come from docs/uplo/business-model.md and
// are an ILLUSTRATIVE EXAMPLE (not market rates); prices are market-test proposals; pipeline cards are demo data.
// Keep those labels wherever these values are shown.

export const ILLUSTRATIVE = "Illustrative example, not market rates";
export const DEMO_DATA = "Demo data · simulated";

export const HERO = {
  eyebrow: "Circular innovation finance",
  line1: "Today's Capital.",
  line2: "Tomorrow's Breakthroughs.",
  sub: "Connecting commercial battery recycling with the next generation of circular innovation.",
  caption: ["Capital", "in motion", "for a cleaner", "tomorrow."],
  pillars: [
    { id: "circular", label: "Circular capital" },
    { id: "industrial", label: "Industrial impact" },
    { id: "innovation", label: "Innovation funding" },
    { id: "solutions", label: "Real-world solutions" },
  ],
} as const;

export const GAP = {
  eyebrow: "The gap",
  left: {
    title: "Recyclers wait 90 days to get paid.",
    body: "Commercial battery recyclers already run at TRL 7–9 and earn revenue - but their buyers pay on 90-day terms, so working capital is tied up in invoices.",
  },
  right: {
    title: "Upcycling research stalls at TRL 4–6.",
    body: "Battery upcycling technologies - direct cathode regeneration, LFP recovery - are proven in the lab but too early for banks and too late for most grants.",
  },
  bridge: "UPLO uses the first to fund the second.",
} as const;

// The capital flow - the defining story of the brand. Five stations, then the loop closes.
export const FLOW = [
  {
    n: "01", id: "assets", title: "Commercial Assets",
    body: "A recycler sells $100,000 of recovered material. The buyer pays in 90 days.",
    figure: { value: 100_000, prefix: "$", label: "Invoice value" },
  },
  {
    n: "02", id: "financing", title: "Financing",
    body: "Verified invoices become working capital today. A financing provider in Pool A advances $95,000 to the recycler now, instead of in 90 days.",
    figure: { value: 95_000, prefix: "$", label: "Advance to the recycler" },
  },
  {
    n: "03", id: "revenue", title: "Platform Revenue",
    body: "At settlement the buyer pays $100,000: $98,000 returns to the financing provider and $2,000 is the platform fee.",
    figure: { value: 2_000, prefix: "$", label: "Platform fee" },
  },
  {
    n: "04", id: "innovation", title: "Innovation Funding",
    body: "After $800 of direct costs, the $1,200 gross contribution sends 20% - $240 - to the Innovation Treasury. Pool B.",
    figure: { value: 240, prefix: "$", label: "To the Innovation Treasury" },
  },
  {
    n: "05", id: "research", title: "Research Development",
    body: "Milestone-gated R&D in battery upcycling: no progress, no money. Funding moves a technology from TRL 4 toward TRL 6.",
    figure: { value: 6, prefix: "TRL ", label: "Validated, milestone by milestone" },
  },
] as const;

export const FLOW_CLOSE = {
  title: "The loop closes.",
  body: "Licensed technology returns to the recyclers that funded it - lower cost, higher recovery, new materials.",
  tagline: "Today's capital. Tomorrow's breakthroughs.",
} as const;

// The $100k waterfall (also used by the Phase 4 calculator).
export const WATERFALL = {
  invoice: 100_000, advance: 95_000, toFinancier: 98_000, platformFee: 2_000,
  directCosts: 800, grossContribution: 1_200, treasuryPct: 0.2, treasury: 240, retained: 960,
} as const;

export const POOLS = {
  eyebrow: "Two pools, never mixed",
  title: "Commercial capital and research capital stay apart.",
  principle: "Investor principal in commercial financing is never used for research.",
  a: {
    tag: "Pool A", title: "Commercial Financing Pool",
    body: "Working capital for recyclers with verifiable transactions.",
    items: ["Investor principal", "Returns per the investor agreement", "Backed by verified, buyer-confirmed invoices"],
  },
  b: {
    tag: "Pool B", title: "Innovation Treasury",
    body: "Funds TRL 4–6 battery upcycling research.",
    items: ["A set share of platform revenue", "Corporate R&D partners", "Backers who accept research risk directly"],
  },
  note: "Four kinds of money are tracked separately: investment capital, investment returns, platform revenue and the innovation treasury. On-chain tokens represent rights only where enforceable legal agreements back them - nothing here is a securities offering.",
} as const;

export const REVENUE = {
  eyebrow: "Three revenue streams",
  title: "Earn now. Build next. Share later.",
  streams: [
    {
      horizon: "Short term", title: "Financing & transaction fees", payer: "Recyclers · financing providers",
      body: "Invoice and receivables financing on verified commercial transactions. Revenue does not wait for research to succeed.",
    },
    {
      horizon: "Mid term", title: "Corporate Innovation Membership", payer: "Recyclers · battery manufacturers · corporate R&D",
      body: "Access to screened research matched to industrial problems, plus validation sprints.",
      tiers: [
        { name: "Research Intelligence", price: "$5,000 / yr" },
        { name: "Innovation Partner", price: "$12,000 / yr" },
        { name: "Strategic R&D Partner", price: "$30,000+ / yr" },
      ],
      tiersNote: "Pricing under market test",
    },
    {
      horizon: "Long term", title: "Licensing success fee / royalty share", payer: "Parties that commercialize the technology",
      body: "A success fee when a supported technology is licensed - or a negotiated royalty share where UPLO materially funds development.",
    },
  ],
} as const;

export const PIPELINE = {
  eyebrow: "Research pipeline",
  title: "TRL 4–6 opportunities, funded milestone by milestone.",
  demo: [
    { title: "Lithium Recovery Enhancement", type: "Process", trl: 6, raised: 350_000, target: 500_000, status: "Funding", impact: "+20% recovery rate", art: "lattice" },
    { title: "Direct Cathode Regeneration", type: "Material", trl: 6, raised: 160_000, target: 250_000, status: "In Progress", impact: "Lower production cost", art: "crystal" },
    { title: "LFP Upcycling Process", type: "Process", trl: 5, raised: 120_000, target: 300_000, status: "Open", impact: "New material application", art: "flow" },
  ],
} as const;

export const TRUST = {
  eyebrow: "Built to be trusted",
  title: "Mechanics you can check, limits we state.",
  points: [
    { id: "escrow", title: "Milestone escrow", body: "Funds release only after an attestor approves the evidence. A missed deadline refunds backers, pro-rata, on-chain." },
    { id: "transparency", title: "On-chain transparency", body: "Raises, milestones, approvals and refunds are public records on Avalanche (Fuji testnet) that anyone can verify." },
    { id: "privacy", title: "Private by design", body: "Matching uses non-confidential categories only. Confidential details are encrypted in your browser - only a hash goes on-chain." },
  ],
  scope: "Testnet demo · mock stablecoin · centralized attestor today.",
} as const;

export const FINALE = {
  title1: "Finance today's industry.",
  title2: "Build tomorrow's technology.",
  marquee: ["People", "Capital", "Research", "Industry", "A cleaner tomorrow"],
} as const;
