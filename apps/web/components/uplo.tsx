import { ArrowRight, ArrowUpRight, Factory, FlaskConical, Info, Radio, RefreshCcw, type LucideIcon } from "lucide-react";
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

// KPI tile, as on the board's dashboard: big figure, label under it, a trend line, and a small 4-bar chart.
export function KpiTile({
  label, value, sub, badge, bars, tone = "lime", trend,
}: {
  label: string; value: ReactNode; sub?: ReactNode; badge: ReactNode;
  bars?: readonly number[]; tone?: "lime" | "copper" | "sage" | "neutral"; trend?: string;
}) {
  const fill = { lime: "bg-lime-500", copper: "bg-copper", sage: "bg-sage", neutral: "bg-charcoal/25" }[tone];
  return (
    <Card className="flex flex-col p-5">
      <div className="flex items-start justify-between gap-2">
        <p className="figure text-[1.75rem] font-semibold leading-none text-charcoal">{value}</p>
        {badge}
      </div>
      <p className="mt-2 text-sm text-charcoal-soft">{label}</p>
      <div className="mt-auto flex items-end justify-between gap-3 pt-3">
        <p className="text-xs text-charcoal-muted">
          {trend && <span className="mr-1 inline-flex items-center font-semibold text-charcoal"><ArrowUpRight aria-hidden className="h-3.5 w-3.5" />{trend}</span>}
          {sub}
        </p>
        {bars && (
          <div aria-hidden className="flex h-8 shrink-0 items-end gap-[3px]">
            {bars.map((b, i) => (
              <span key={i} className={cx("w-[5px] rounded-sm", i === bars.length - 1 ? fill : "bg-charcoal/15")} style={{ height: `${Math.max(0.15, b) * 100}%` }} />
            ))}
          </div>
        )}
      </div>
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
// Capital Flow, as on the board's dashboard: Commercial Battery Recycling (TRL 7-9) → the UPLO ring (lime = capital,
// copper = industry) → Innovation Funding → Research & Development (TRL 4-6). The loop closes with licensed
// technology returning to industry.
// ---------------------------------------------------------------------------------------------------------------

function FlowBox({ icon: Icon, title, sub, wide }: { icon?: LucideIcon; title: string; sub?: string; wide?: boolean }) {
  return (
    <div className={cx("flex flex-col items-center justify-center rounded-xl bg-limestone-100 px-4 py-5 text-center ring-1 ring-inset ring-neutral/70",
      wide ? "min-h-[8.5rem] md:w-48" : "min-h-[6rem] md:w-36")}>
      {Icon && <Icon aria-hidden className="mb-2 h-8 w-8 text-charcoal" strokeWidth={1.3} />}
      <p className="text-sm font-semibold leading-snug text-charcoal">{title}</p>
      {sub && <p className="mt-0.5 text-xs text-charcoal-muted">{sub}</p>}
    </div>
  );
}

function FlowArrow() {
  return <ArrowRight aria-hidden className="mx-auto h-5 w-5 shrink-0 rotate-90 text-charcoal md:rotate-0" strokeWidth={1.5} />;
}

// Ring colours, clockwise from 12 o'clock: lime arc (capital), copper arc (industry).
const RING = ["#D7EB79", "#D7EB79", "#D7EB79", "#B57856", "#B57856", "#B57856", "#D7EB79"] as const;

export function UploRing({ className }: { className?: string }) {
  return (
    <div className={cx("relative grid aspect-square place-items-center", className)}>
      <svg viewBox="0 0 200 200" className="absolute inset-0 h-full w-full" aria-hidden>
        {RING.map((c, i) => <path key={i} d={sectorPath(i, RING.length)} fill={c} />)}
      </svg>
      {/* TODO(logo): replace with the official wordmark once apps/web/public/brand/ has the PNGs */}
      <span className="relative font-display text-lg font-bold tracking-tight text-charcoal">UPLO</span>
    </div>
  );
}

export function CapitalFlowDiagram({ className }: { className?: string }) {
  return (
    <figure className={className}
      aria-label="Capital flow: commercial battery recycling at TRL 7 to 9 is financed through UPLO; part of the platform margin funds the Innovation Treasury, which funds milestone-gated research at TRL 4 to 6; licensed technology flows back to recyclers.">
      <div className="flex flex-col items-center gap-3 md:flex-row md:justify-between md:gap-4">
        <FlowBox icon={Factory} title="Commercial Battery Recycling" sub="(TRL 7–9)" wide />
        <FlowArrow />
        <UploRing className="w-32 md:w-36" />
        <FlowArrow />
        <FlowBox title="Innovation Funding" sub="Pool B" />
        <FlowArrow />
        <FlowBox icon={FlaskConical} title="Research & Development" sub="(TRL 4–6)" wide />
      </div>
      <figcaption className="mt-5 grid gap-2 text-xs text-charcoal-muted sm:grid-cols-3">
        <span className="flex items-center gap-2"><span aria-hidden className="h-2.5 w-2.5 rounded-sm bg-copper" />Pool A finances verified invoices</span>
        <span className="flex items-center gap-2"><span aria-hidden className="h-2.5 w-2.5 rounded-sm bg-lime-500" />20% of platform margin → Innovation Treasury</span>
        <span className="flex items-center gap-2"><RefreshCcw aria-hidden className="h-3.5 w-3.5 text-charcoal" />Licensed technology returns to industry</span>
      </figcaption>
    </figure>
  );
}
