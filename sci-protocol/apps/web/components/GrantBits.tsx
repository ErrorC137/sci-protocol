"use client";

import type { Grant, RuleResult, ScoreBreakdown } from "@sci/shared";
import { useEffect, useState } from "react";
import { awardRange, countdown } from "@/lib/format";
import { Bar, Chip, cx } from "./ui";

const TYPE_TONE: Record<string, "blue" | "violet" | "green" | "amber" | "slate"> = {
  government: "blue", accelerator: "violet", foundation: "green", web3: "amber", crowdfunding: "green", corporate: "slate",
};

export function GrantMeta({ g }: { g: Grant }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {g.funder_type && <Chip tone={TYPE_TONE[g.funder_type] ?? "slate"}>{g.funder_type}</Chip>}
      {g.eligible_countries.length === 1 && g.eligible_countries[0] !== "*" && <Chip>{g.eligible_countries[0]} only</Chip>}
      {g.eligible_countries[0] === "*" && <Chip>Global</Chip>}
      <Chip>{awardRange(g.amount_min_usd, g.amount_max_usd)}</Chip>
      {g.equity_taken === true && <Chip tone="red">takes equity</Chip>}
      {g.equity_taken === false && <Chip tone="green">non-dilutive</Chip>}
      {(g.trl_min || g.trl_max) && <Chip>TRL {g.trl_min ?? 1}-{g.trl_max ?? 9}</Chip>}
      {g.verified ? <Chip tone="green">verified</Chip> : <Chip tone="amber" title="Curated from general knowledge - check the funder's site">unverified</Chip>}
      {g.source !== "curated" && <Chip tone="blue">live: {g.source}</Chip>}
    </div>
  );
}

export function Deadline({ g }: { g: Grant }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(t);
  }, []);
  if (g.rolling) return <span className="text-sm text-emerald-700">Rolling - apply any time</span>;
  if (!g.deadline) return <span className="text-sm text-ink-muted">Deadline not confirmed{g.cycle_note ? ` · ${g.cycle_note}` : ""}</span>;
  const secs = (new Date(g.deadline).getTime() - now) / 1000;
  return (
    <span className={cx("text-sm", secs < 14 * 86400 ? "font-semibold text-rose-700" : "text-ink-soft")}>
      Closes {new Date(g.deadline).toLocaleDateString()} · {countdown(secs)} left
    </span>
  );
}

const RULE_LABEL: Record<string, string> = {
  country: "Country", applicant_type: "Applicant", trl: "TRL", amount: "Amount", deadline: "Deadline",
  incorporation: "Entity", equity: "Equity", ip: "IP",
};

export function RuleList({ rules, compact }: { rules: RuleResult[]; compact?: boolean }) {
  return (
    <ul className={cx("grid gap-1 text-xs", compact ? "sm:grid-cols-2" : "")}>
      {rules.map((r) => (
        <li key={r.rule} className="flex gap-1.5">
          <span className={cx("font-bold", r.status === "pass" ? "text-emerald-600" : r.status === "fail" ? "text-rose-600" : "text-amber-600")}>
            {r.status === "pass" ? "✓" : r.status === "fail" ? "✗" : "?"}
          </span>
          <span className="text-ink-soft"><span className="font-medium text-ink">{RULE_LABEL[r.rule] ?? r.rule}:</span> {r.detail}</span>
        </li>
      ))}
    </ul>
  );
}

const COMPONENTS: [keyof ScoreBreakdown, string, number][] = [
  ["similarity", "Similarity", 0.45],
  ["field_overlap", "Field overlap", 0.2],
  ["trl_centering", "TRL fit", 0.15],
  ["amount_fit", "Amount fit", 0.1],
  ["deadline_feasibility", "Deadline runway", 0.1],
];

export function ScoreBars({ s, boost }: { s: ScoreBreakdown; boost?: number }) {
  return (
    <div className="space-y-1.5">
      {COMPONENTS.map(([k, label, w]) => (
        <div key={k} className="grid grid-cols-[7.5rem_1fr_2.5rem] items-center gap-2 text-xs text-ink-muted">
          <span>{label} <span className="text-slate-400">×{w}</span></span>
          <Bar value={s[k]} />
          <span className="text-right tabular-nums">{Math.round(s[k] * 100)}</span>
        </div>
      ))}
      {boost !== undefined && boost > 0 && (
        <p className="text-xs text-emerald-700">+{Math.round(boost * 100)} local keyword boost (computed in your browser, never sent)</p>
      )}
    </div>
  );
}
