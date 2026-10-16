// ALL simulated UPLO numbers live in this one file, so they are easy to find, swap or delete.
//
// Nothing here is traction. Every screen that renders a value from this file must show the DEMO_BADGE label
// ("Demo data · simulated") next to it. The $100k waterfall is the ILLUSTRATIVE example from
// docs/uplo/business-model.md (not market rates). Membership prices are market-test proposals.
// Recyclers and buyers are anonymised placeholders on purpose: we do not name real companies as customers.

export const DEMO_BADGE = "Demo data · simulated";
export const ILLUSTRATIVE_BADGE = "Illustrative example, not market rates";

// ---------------------------------------------------------------------------------------------------------------
// Invoice-financing waterfall (business-model.md, "illustrative invoice example")
// ---------------------------------------------------------------------------------------------------------------

export interface WaterfallInput {
  invoice: number; // verified invoice value, USD
  advancePct: number; // share of the invoice advanced to the recycler today (0-1)
  feePct: number; // platform fee, share of the invoice (0-1)
  directCostPct: number; // direct operating cost of the transaction, share of the invoice (0-1)
  treasuryPct: number; // share of the gross contribution allocated to the Innovation Treasury (0-1)
  termDays: number; // buyer payment term
}

export interface Waterfall extends WaterfallInput {
  advance: number; // paid to the recycler now (Pool A)
  toFinancier: number; // returned to the financing provider at settlement: invoice - platform fee
  financierSpread: number; // toFinancier - advance, before losses and costs
  platformFee: number;
  directCosts: number;
  grossContribution: number; // platformFee - directCosts
  treasury: number; // -> Pool B
  retained: number; // stays with the platform
  recyclerCost: number; // invoice - advance: what early payment costs the recycler
}

export const DEFAULT_WATERFALL: WaterfallInput = {
  invoice: 100_000, advancePct: 0.95, feePct: 0.02, directCostPct: 0.008, treasuryPct: 0.2, termDays: 90,
};

export function settle(i: WaterfallInput): Waterfall {
  const advance = i.invoice * i.advancePct;
  const platformFee = i.invoice * i.feePct;
  const toFinancier = i.invoice - platformFee;
  const directCosts = i.invoice * i.directCostPct;
  const grossContribution = platformFee - directCosts;
  // A negative contribution allocates nothing: the treasury is funded from margin, never from principal.
  const treasury = Math.max(0, grossContribution) * i.treasuryPct;
  return {
    ...i, advance, toFinancier, financierSpread: toFinancier - advance, platformFee, directCosts, grossContribution,
    treasury, retained: grossContribution - treasury, recyclerCost: i.invoice - advance,
  };
}

/** The canonical example: $100k → $95k advance, $98k to the financier, $2k fee, $1.2k contribution, $240 to Pool B. */
export const WATERFALL = settle(DEFAULT_WATERFALL);

// ---------------------------------------------------------------------------------------------------------------
// Commercial Finance (Pool A) - simulated invoice book
// ---------------------------------------------------------------------------------------------------------------

export type InvoiceStatus = "verified" | "advanced" | "settled" | "pending";

export interface DemoInvoice {
  id: string;
  recycler: string;
  material: string;
  buyer: string;
  amount: number;
  issued: string; // ISO date
  due: string; // ISO date
  advancePct: number;
  status: InvoiceStatus;
}

export const DEMO_INVOICES: DemoInvoice[] = [
  { id: "INV-0142", recycler: "Recycler A", material: "Black mass (NMC)", buyer: "Cathode producer 1", amount: 100_000, issued: "2026-09-02", due: "2026-12-01", advancePct: 0.95, status: "advanced" },
  { id: "INV-0145", recycler: "Recycler B", material: "Recovered copper foil", buyer: "Metals trader 2", amount: 64_500, issued: "2026-09-10", due: "2026-12-09", advancePct: 0.9, status: "advanced" },
  { id: "INV-0151", recycler: "Recycler A", material: "Lithium carbonate", buyer: "Cell manufacturer 3", amount: 182_000, issued: "2026-09-21", due: "2026-12-20", advancePct: 0.95, status: "verified" },
  { id: "INV-0153", recycler: "Recycler C", material: "LFP scrap, sorted", buyer: "Cathode producer 1", amount: 41_200, issued: "2026-09-28", due: "2026-12-27", advancePct: 0.85, status: "pending" },
  { id: "INV-0127", recycler: "Recycler B", material: "Black mass (LFP)", buyer: "Refiner 4", amount: 88_000, issued: "2026-06-15", due: "2026-09-13", advancePct: 0.95, status: "settled" },
  { id: "INV-0119", recycler: "Recycler C", material: "Nickel sulphate", buyer: "Cell manufacturer 3", amount: 120_400, issued: "2026-06-01", due: "2026-08-30", advancePct: 0.9, status: "settled" },
];

export const INVOICE_STATUS_LABEL: Record<InvoiceStatus, string> = {
  pending: "Awaiting verification", verified: "Verified", advanced: "Advanced", settled: "Settled",
};

// ---------------------------------------------------------------------------------------------------------------
// Overview KPIs (the brand board's mock-up figures - demo only, never real metrics)
// ---------------------------------------------------------------------------------------------------------------

export const DEMO_KPIS = {
  verifiedAssets: { value: 2_400_000, delta: "+23%", bars: [0.45, 0.6, 0.72, 1] },
  activeFinancing: { value: 950_000, delta: "+18%", bars: [0.5, 0.62, 0.8, 1] },
  innovationCapital: { value: 38_000, delta: "+56%", bars: [0.35, 0.55, 0.78, 1] },
  researchProjects: { value: 6, delta: "In validation", bars: [0.4, 0.7, 0.55, 1] },
} as const;

// ---------------------------------------------------------------------------------------------------------------
// Research pipeline - demo opportunities (landing S6 and the Overview table)
// ---------------------------------------------------------------------------------------------------------------

export interface DemoOpportunity {
  title: string;
  type: "Process" | "Material" | "Equipment";
  trl: number;
  raised: number;
  target: number;
  status: "Open" | "Funding" | "In Progress";
  impact: string;
  art: "lattice" | "crystal" | "flow";
}

export const DEMO_OPPORTUNITIES: DemoOpportunity[] = [
  { title: "Lithium Recovery Enhancement", type: "Process", trl: 6, raised: 350_000, target: 500_000, status: "Funding", impact: "+20% recovery rate", art: "lattice" },
  { title: "Direct Cathode Regeneration", type: "Material", trl: 6, raised: 160_000, target: 250_000, status: "In Progress", impact: "Lower production cost", art: "crystal" },
  { title: "LFP Upcycling Process", type: "Process", trl: 5, raised: 120_000, target: 300_000, status: "Open", impact: "New material application", art: "flow" },
];
