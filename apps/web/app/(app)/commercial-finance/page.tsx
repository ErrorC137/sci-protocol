"use client";

import { RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";
import { DemoBadge, FootNote, KpiTile, SectionTitle, compactMoney, money } from "@/components/uplo";
import { Card, Chip, Notice, PageHeader, StatusChip, inputCls } from "@/components/ui";
import {
  DEFAULT_WATERFALL, DEMO_INVOICES, ILLUSTRATIVE_BADGE, INVOICE_STATUS_LABEL, settle, type DemoInvoice, type WaterfallInput,
} from "@/lib/uplo-demo-data";

const th = "px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-eyebrow text-charcoal-muted";
const td = "px-4 py-3 align-middle";
const date = (iso: string) => new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

function InvoiceStatus({ s }: { s: DemoInvoice["status"] }) {
  if (s === "verified") return <StatusChip status="verified" />;
  if (s === "advanced") return <StatusChip status="progress">{INVOICE_STATUS_LABEL.advanced}</StatusChip>;
  if (s === "settled") return <StatusChip status="completed">{INVOICE_STATUS_LABEL.settled}</StatusChip>;
  return <Chip>{INVOICE_STATUS_LABEL.pending}</Chip>;
}

function PctField({ label, hint, value, onChange, min, max, step }: {
  label: string; hint: string; value: number; onChange: (v: number) => void; min: number; max: number; step: number;
}) {
  const id = label.toLowerCase().replace(/[^a-z]+/g, "-");
  const shown = +(value * 100).toFixed(2);
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <label htmlFor={id} className="text-sm font-semibold text-charcoal">{label}</label>
        <span className="figure text-sm text-charcoal">{shown}%</span>
      </div>
      <input id={id} type="range" min={min} max={max} step={step} value={shown} aria-describedby={`${id}-hint`}
        onChange={(e) => onChange(Number(e.target.value) / 100)} className="mt-2 w-full accent-charcoal" />
      <p id={`${id}-hint`} className="text-xs text-charcoal-muted">{hint}</p>
    </div>
  );
}

function Calculator() {
  const [input, setInput] = useState<WaterfallInput>(DEFAULT_WATERFALL);
  const w = useMemo(() => settle(input), [input]);
  const set = (k: keyof WaterfallInput) => (v: number) => setInput((s) => ({ ...s, [k]: v }));
  const spreadNegative = w.financierSpread < 0;
  const marginNegative = w.grossContribution < 0;
  const annualised = w.advance > 0 ? (w.financierSpread / w.advance) * (365 / w.termDays) : 0;

  // Where every dollar of the invoice ends up. Order = left to right in the bar.
  const parts = [
    { label: "Advance to the recycler, today", value: w.advance, cls: "bg-charcoal", pool: "Pool A" },
    { label: "Financing provider's spread", value: Math.max(0, w.financierSpread), cls: "bg-copper", pool: "Pool A" },
    { label: "Direct costs", value: Math.min(w.directCosts, w.platformFee), cls: "bg-neutral", pool: "Platform" },
    { label: "Platform retained", value: Math.max(0, w.retained), cls: "bg-sage", pool: "Platform" },
    { label: "Innovation Treasury", value: w.treasury, cls: "bg-lime-500", pool: "Pool B" },
  ];
  const total = parts.reduce((s, p) => s + p.value, 0) || 1;

  const rows: [string, number, string?][] = [
    ["Verified invoice value", w.invoice],
    [`Advance to the recycler now (${+(w.advancePct * 100).toFixed(2)}%)`, w.advance],
    [`Buyer pays at day ${w.termDays}`, w.invoice],
    ["Returned to the financing provider", w.toFinancier, `spread ${money(w.financierSpread)}`],
    [`Platform fee (${+(w.feePct * 100).toFixed(2)}%)`, w.platformFee],
    ["Direct costs", -w.directCosts],
    ["Gross contribution", w.grossContribution],
    [`→ Innovation Treasury (${Math.round(w.treasuryPct * 100)}% of contribution)`, w.treasury, "Pool B"],
    ["Retained by the platform", w.retained],
  ];

  return (
    <Card className="p-6">
      <SectionTitle eyebrow="Calculator" title="How a verified invoice settles"
        aside={<div className="flex flex-wrap items-center gap-2"><DemoBadge>{ILLUSTRATIVE_BADGE}</DemoBadge>
          <button type="button" onClick={() => setInput(DEFAULT_WATERFALL)}
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-semibold text-charcoal hover:bg-charcoal/5">
            <RotateCcw aria-hidden className="h-3.5 w-3.5" />Reset to $100k example
          </button></div>} />

      <div className="grid gap-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <div className="space-y-5">
          <div>
            <label htmlFor="invoice" className="text-sm font-semibold text-charcoal">Invoice value (USD)</label>
            <input id="invoice" type="number" min={1000} step={1000} inputMode="numeric" value={input.invoice}
              onChange={(e) => set("invoice")(Math.max(0, Number(e.target.value) || 0))} className={`${inputCls} figure mt-1.5`} />
          </div>
          <PctField label="Advance rate" hint="Share of the invoice paid to the recycler today." value={input.advancePct} onChange={set("advancePct")} min={70} max={99} step={0.5} />
          <PctField label="Platform fee" hint="Share of the invoice, charged at settlement." value={input.feePct} onChange={set("feePct")} min={0} max={6} step={0.1} />
          <PctField label="Direct costs" hint="Verification, servicing and transaction costs, as a share of the invoice." value={input.directCostPct} onChange={set("directCostPct")} min={0} max={3} step={0.1} />
          <PctField label="Treasury allocation" hint="Share of the gross contribution sent to the Innovation Treasury." value={input.treasuryPct} onChange={set("treasuryPct")} min={0} max={50} step={1} />
          <div>
            <label htmlFor="term" className="text-sm font-semibold text-charcoal">Buyer payment term (days)</label>
            <input id="term" type="number" min={15} max={180} step={15} value={input.termDays}
              onChange={(e) => set("termDays")(Math.min(365, Math.max(1, Number(e.target.value) || 90)))} className={`${inputCls} figure mt-1.5`} />
          </div>
        </div>

        <div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div className="rounded-lg bg-charcoal p-4 text-limestone-50">
              <p className="text-[11px] font-semibold uppercase tracking-eyebrow text-limestone-400">Recycler gets today</p>
              <p className="figure mt-1 text-2xl font-semibold text-lime">{money(w.advance)}</p>
            </div>
            <div className="rounded-lg border border-neutral p-4">
              <p className="eyebrow">Platform fee</p>
              <p className="figure mt-1 text-2xl font-semibold text-charcoal">{money(w.platformFee)}</p>
            </div>
            <div className="col-span-2 rounded-lg border border-lime-300 bg-lime-50 p-4 sm:col-span-1">
              <p className="text-[11px] font-semibold uppercase tracking-eyebrow text-lime-800">To Pool B</p>
              <p className="figure mt-1 text-2xl font-semibold text-charcoal">{money(w.treasury)}</p>
            </div>
          </div>

          <div className="mt-5" role="img" aria-label={parts.map((p) => `${p.label}: ${money(p.value)}`).join("; ")}>
            <div className="flex h-4 w-full overflow-hidden rounded-full bg-charcoal/10">
              {parts.map((p) => <div key={p.label} className={p.cls} style={{ width: `${(p.value / total) * 100}%` }} />)}
            </div>
            {/* The margin is tiny next to the advance, so zoom in on the fee itself. */}
            <p className="mt-3 text-xs font-semibold text-charcoal-muted">Zoom: the platform fee</p>
            <div className="mt-1 flex h-3 w-full overflow-hidden rounded-full bg-charcoal/10">
              {parts.slice(2).map((p) => <div key={p.label} className={p.cls} style={{ width: `${w.platformFee > 0 ? (p.value / w.platformFee) * 100 : 0}%` }} />)}
            </div>
            <ul className="mt-3 grid gap-x-6 gap-y-1.5 text-xs sm:grid-cols-2">
              {parts.map((p) => (
                <li key={p.label} className="flex items-center gap-2">
                  <span aria-hidden className={`h-2.5 w-2.5 shrink-0 rounded-sm ${p.cls}`} />
                  <span className="text-charcoal-soft">{p.label} <span className="text-charcoal-muted">· {p.pool}</span></span>
                  <span className="figure ml-auto text-charcoal">{money(p.value)}</span>
                </li>
              ))}
            </ul>
          </div>

          <table className="mt-5 w-full text-sm">
            <caption className="sr-only">Settlement waterfall</caption>
            <tbody>
              {rows.map(([l, v, note]) => (
                <tr key={l} className="border-t border-neutral">
                  <th scope="row" className="py-2 pr-3 text-left font-normal text-charcoal-soft">{l}{note && <span className="ml-1 text-xs text-charcoal-muted">({note})</span>}</th>
                  <td className="figure py-2 text-right font-medium text-charcoal">{money(v)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="mt-4 space-y-2">
            {spreadNegative && <Notice tone="danger">The fee is larger than the discount, so the financing provider would get back less than it advanced. No provider would fund this.</Notice>}
            {marginNegative && <Notice tone="caution">Direct costs exceed the fee: the transaction loses money and nothing is allocated to the treasury.</Notice>}
            {!spreadNegative && w.advance > 0 && (
              <p className="text-xs text-charcoal-muted">
                Early payment costs the recycler {money(w.recyclerCost)} ({((w.recyclerCost / (w.invoice || 1)) * 100).toFixed(1)}% of the invoice).
                The provider&apos;s spread is {money(w.financierSpread)}, about {(annualised * 100).toFixed(1)}% annualised before losses and costs.
              </p>
            )}
          </div>
        </div>
      </div>
      <FootNote>The treasury allocation comes from platform margin only. Investor principal and returns stay in Pool A and are never used for research.</FootNote>
    </Card>
  );
}

export default function CommercialFinance() {
  const open = DEMO_INVOICES.filter((i) => i.status !== "settled");
  const settled = DEMO_INVOICES.filter((i) => i.status === "settled");
  const advanced = DEMO_INVOICES.filter((i) => i.status === "advanced").reduce((s, i) => s + i.amount * i.advancePct, 0);
  const treasury = settled.reduce((s, i) => s + settle({ ...DEFAULT_WATERFALL, invoice: i.amount, advancePct: i.advancePct }).treasury, 0);

  return (
    <div className="space-y-10">
      <PageHeader eyebrow="Pool A · Commercial Financing" title="Verified invoices become working capital today.">
        Battery recyclers already earn revenue, but their buyers pay on 90-day terms. Pool A advances cash against
        verified, buyer-confirmed invoices. When the buyer pays, the financing provider is repaid and a share of the
        platform margin flows to the Innovation Treasury.
      </PageHeader>

      <Notice tone="caution">
        <strong>Simulated.</strong> No real financing happens on this page, and no contract or wallet is involved.
        Real invoice financing would need licensed financing partners, KYC, and legal agreements with recyclers and buyers.
      </Notice>

      <section>
        <SectionTitle eyebrow="Invoice book" title="Pool A at a glance" aside={<DemoBadge />} />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiTile label="Open invoices" value={open.length} sub={`${compactMoney(open.reduce((s, i) => s + i.amount, 0))} face value`} badge={<DemoBadge>Demo</DemoBadge>} tone="copper" />
          <KpiTile label="Advanced, outstanding" value={compactMoney(advanced)} sub="Cash already paid to recyclers" badge={<DemoBadge>Demo</DemoBadge>} tone="neutral" />
          <KpiTile label="Settled" value={settled.length} sub={`${compactMoney(settled.reduce((s, i) => s + i.amount, 0))} repaid by buyers`} badge={<DemoBadge>Demo</DemoBadge>} tone="sage" />
          <KpiTile label="Sent to Pool B" value={money(treasury)} sub="From settled invoices' margin" badge={<DemoBadge>Demo</DemoBadge>} tone="lime" />
        </div>
      </section>

      <section>
        <SectionTitle eyebrow="Verified transactions" title="Invoices" aside={<DemoBadge />} />
        <div className="overflow-x-auto rounded-xl border border-neutral bg-white">
          <table className="w-full min-w-[820px] text-sm">
            <thead className="bg-limestone-50">
              <tr><th className={th}>Invoice</th><th className={th}>Recycler · material</th><th className={th}>Buyer</th><th className={`${th} text-right`}>Amount</th><th className={th}>Due</th><th className={`${th} text-right`}>Advance</th><th className={th}>Status</th></tr>
            </thead>
            <tbody>
              {DEMO_INVOICES.map((i) => (
                <tr key={i.id} className="border-t border-neutral">
                  <td className={`${td} figure whitespace-nowrap font-medium text-charcoal`}>{i.id}</td>
                  <td className={td}><span className="font-medium text-charcoal">{i.recycler}</span><span className="block text-xs text-charcoal-muted">{i.material}</span></td>
                  <td className={`${td} text-charcoal-soft`}>{i.buyer}</td>
                  <td className={`${td} figure text-right text-charcoal`}>{money(i.amount)}</td>
                  <td className={`${td} figure text-charcoal-soft`}>{date(i.due)}</td>
                  <td className={`${td} figure text-right text-charcoal-soft`}>{Math.round(i.advancePct * 100)}%</td>
                  <td className={td}><InvoiceStatus s={i.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <FootNote>Recyclers and buyers are anonymised placeholders, not customers or partners.</FootNote>
      </section>

      <Calculator />
    </div>
  );
}
