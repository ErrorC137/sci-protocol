import { FlaskConical, Info, Radio } from "lucide-react";
import type { ReactNode } from "react";
import { DEMO_BADGE } from "@/lib/uplo-demo-data";
import { sectorPath } from "./landing/RingSvg";
import { Card, cx } from "./ui";

// Shared pieces for the UPLO demo layer (Overview, Commercial Finance, Validation).

/** Every simulated figure carries this. Text + icon, so it never relies on colour. */
export function DemoBadge({ children = DEMO_BADGE, className }: { children?: ReactNode; className?: string }) {
  return (
    <span className={cx("inline-flex items-center gap-1 rounded-full bg-copper-50 px-2 py-0.5 text-[11px] font-semibold text-copper-700 ring-1 ring-inset ring-copper-200", className)}>
      <FlaskConical aria-hidden className="h-3 w-3" />{children}
    </span>
  );
}

/** Values read live from the chain or the API. */
export function LiveBadge({ children = "Live", className }: { children?: ReactNode; className?: string }) {
  return (
    <span className={cx("inline-flex items-center gap-1 rounded-full bg-lime-100 px-2 py-0.5 text-[11px] font-semibold text-lime-800 ring-1 ring-inset ring-lime-300", className)}>
      <Radio aria-hidden className="h-3 w-3" />{children}
    </span>
  );
}

export function KpiTile({
  label, value, sub, badge, accent = "lime",
}: { label: string; value: ReactNode; sub?: ReactNode; badge: ReactNode; accent?: "lime" | "copper" | "sage" | "charcoal" }) {
  const bar = { lime: "bg-lime-500", copper: "bg-copper", sage: "bg-sage", charcoal: "bg-charcoal" }[accent];
  return (
    <Card className="relative overflow-hidden">
      <span aria-hidden className={cx("absolute inset-x-0 top-0 h-1", bar)} />
      <div className="flex items-start justify-between gap-2">
        <p className="eyebrow">{label}</p>
        {badge}
      </div>
      <p className="figure mt-3 text-3xl font-semibold text-charcoal">{value}</p>
      {sub && <p className="mt-1 text-xs text-charcoal-muted">{sub}</p>}
    </Card>
  );
}

export function SectionTitle({ eyebrow, title, aside }: { eyebrow?: string; title: string; aside?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2 className="mt-1 font-display text-xl font-semibold text-charcoal">{title}</h2>
      </div>
      {aside}
    </div>
  );
}

export function FootNote({ children }: { children: ReactNode }) {
  return (
    <p className="mt-3 flex items-start gap-1.5 text-xs text-charcoal-muted">
      <Info aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>{children}</span>
    </p>
  );
}

export const money = (n: number, digits = 0) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: digits, minimumFractionDigits: digits });

export const compactMoney = (n: number) =>
  n >= 1e6 ? `$${(n / 1e6).toFixed(1).replace(/\.0$/, "")}M` : n >= 1e3 ? `$${Math.round(n / 1e3)}K` : money(n);

// ---------------------------------------------------------------------------------------------------------------
// Capital Flow: Commercial Battery Recycling (TRL 7-9) → UPLO → Innovation Funding → Research & Development
// (TRL 4-6), with licensed technology flowing back. Lime = capital, copper = the industrial return.
// ---------------------------------------------------------------------------------------------------------------

const NODES = [
  { x: 10, title: ["Commercial Battery", "Recycling"], tag: "TRL 7–9", note: "Verified invoices", accent: "#B57856" },
  { x: 470, title: ["Innovation", "Funding"], tag: "Pool B", note: "Innovation Treasury", accent: "#D7EB79" },
  { x: 770, title: ["Research &", "Development"], tag: "TRL 4–6", note: "Milestone-gated", accent: "#A7B8A1" },
] as const;
const NODE_W = 180, NODE_H = 116, NODE_Y = 70;
const RING_CX = 320, RING_CY = NODE_Y + NODE_H / 2, RING_R = 64;

function FlowNode({ x, title, tag, note, accent }: (typeof NODES)[number]) {
  return (
    <g transform={`translate(${x} ${NODE_Y})`}>
      <rect width={NODE_W} height={NODE_H} rx={12} fill="#FFFFFF" stroke="#D9D9D6" />
      <rect width={4} height={NODE_H - 24} y={12} rx={2} fill={accent} />
      <text x={18} y={30} className="fill-charcoal-muted" fontSize={10} fontWeight={600} letterSpacing="0.16em">{tag.toUpperCase()}</text>
      {title.map((t, i) => (
        <text key={t} x={18} y={54 + i * 20} className="fill-charcoal font-display" fontSize={16} fontWeight={600}>{t}</text>
      ))}
      <text x={18} y={NODE_H - 14} className="fill-charcoal-muted" fontSize={11}>{note}</text>
    </g>
  );
}

function FlowLabel({ x, y, children }: { x: number; y: number; children: string }) {
  return <text x={x} y={y} textAnchor="middle" className="fill-charcoal-soft" fontSize={11} fontWeight={500}>{children}</text>;
}

export function CapitalFlowDiagram({ className }: { className?: string }) {
  const y = RING_CY;
  const scale = (RING_R * 2) / 200;
  return (
    <div className={className}>
      {/* Wide screens: the diagram */}
      <svg viewBox="0 0 960 300" className="hidden w-full sm:block" role="img"
        aria-label="Capital flow: commercial battery recycling at TRL 7 to 9 is financed through UPLO; part of the platform margin funds the Innovation Treasury, which funds milestone-gated research at TRL 4 to 6; licensed technology flows back to recyclers.">
        {/* forward capital lines */}
        <line x1={NODES[0].x + NODE_W} y1={y} x2={RING_CX - RING_R - 6} y2={y} className="flow-line" stroke="#B3CB45" strokeWidth={3} />
        <line x1={RING_CX + RING_R + 6} y1={y} x2={NODES[1].x} y2={y} className="flow-line" stroke="#B3CB45" strokeWidth={3} />
        <line x1={NODES[1].x + NODE_W} y1={y} x2={NODES[2].x} y2={y} className="flow-line" stroke="#B3CB45" strokeWidth={3} />
        {[NODES[1].x, NODES[2].x, RING_CX - RING_R - 6].map((ax) => (
          <path key={ax} d={`M ${ax - 9} ${y - 6} L ${ax} ${y} L ${ax - 9} ${y + 6}`} fill="none" stroke="#5F6F1F" strokeWidth={2} />
        ))}
        <FlowLabel x={(NODES[0].x + NODE_W + RING_CX - RING_R) / 2} y={y - 14}>Financing</FlowLabel>
        <FlowLabel x={(NODES[0].x + NODE_W + RING_CX - RING_R) / 2} y={y + 24}>Pool A</FlowLabel>
        <FlowLabel x={(RING_CX + RING_R + NODES[1].x) / 2} y={y - 14}>20% of margin</FlowLabel>
        <FlowLabel x={(NODES[1].x + NODE_W + NODES[2].x) / 2} y={y - 14}>Escrow</FlowLabel>

        {/* return path: licensed technology back to industry */}
        <path d={`M ${NODES[2].x + NODE_W / 2} ${NODE_Y + NODE_H} C ${NODES[2].x + NODE_W / 2} 268, ${NODES[0].x + NODE_W / 2} 268, ${NODES[0].x + NODE_W / 2} ${NODE_Y + NODE_H}`}
          fill="none" stroke="#B57856" strokeWidth={2} className="flow-line flow-line-slow" />
        <path d={`M ${NODES[0].x + NODE_W / 2 - 6} ${NODE_Y + NODE_H + 10} L ${NODES[0].x + NODE_W / 2} ${NODE_Y + NODE_H + 1} L ${NODES[0].x + NODE_W / 2 + 6} ${NODE_Y + NODE_H + 10}`}
          fill="none" stroke="#7A4A2F" strokeWidth={2} />
        <text x={480} y={288} textAnchor="middle" className="fill-copper-700" fontSize={11} fontWeight={600} letterSpacing="0.14em">LICENSED TECHNOLOGY RETURNS TO INDUSTRY</text>

        {/* the UPLO ring */}
        <g transform={`translate(${RING_CX - RING_R} ${RING_CY - RING_R}) scale(${scale})`}>
          {Array.from({ length: 5 }, (_, i) => <path key={i} d={sectorPath(i, 5)} fill="#D7EB79" stroke="#1E2320" strokeWidth={1.2} />)}
        </g>
        <text x={RING_CX} y={RING_CY + 6} textAnchor="middle" className="fill-charcoal font-display" fontSize={18} fontWeight={700}>UPLO</text>
        <text x={RING_CX} y={RING_CY - RING_R - 14} textAnchor="middle" className="fill-charcoal-muted" fontSize={10} fontWeight={600} letterSpacing="0.16em">PLATFORM REVENUE</text>

        {NODES.map((n) => <FlowNode key={n.x} {...n} />)}
      </svg>

      {/* Phones: the same flow as a list */}
      <ol className="space-y-2 sm:hidden">
        {[
          ["Commercial Battery Recycling", "TRL 7–9 · verified invoices"],
          ["Financing through UPLO", "Pool A advances working capital"],
          ["Platform revenue", "20% of the margin → Innovation Treasury"],
          ["Innovation Funding", "Pool B · milestone escrow"],
          ["Research & Development", "TRL 4–6 battery upcycling"],
          ["Licensed technology", "returns to industry - the loop closes"],
        ].map(([t, s], i) => (
          <li key={t} className="flex items-start gap-3 rounded-lg border border-neutral bg-white p-3">
            <span className="figure grid h-7 w-7 shrink-0 place-items-center rounded-full bg-charcoal text-xs text-lime">{String(i + 1).padStart(2, "0")}</span>
            <span><span className="block text-sm font-semibold text-charcoal">{t}</span><span className="text-xs text-charcoal-muted">{s}</span></span>
          </li>
        ))}
      </ol>
    </div>
  );
}
