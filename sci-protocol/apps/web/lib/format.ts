import { formatUnits } from "viem";

export const usd = (n: number | null | undefined) =>
  n === null || n === undefined ? "?" : n >= 1e6 ? `$${(n / 1e6).toFixed(n % 1e6 ? 1 : 0)}M` : n >= 1e3 ? `$${Math.round(n / 1e3)}k` : `$${Math.round(n)}`;

export function awardRange(min: number | null, max: number | null): string {
  if (min === null && max === null) return "Amount not stated";
  if (min !== null && max !== null && min === max) return usd(max);
  if (!min) return `up to ${usd(max)}`;
  if (max === null) return `from ${usd(min)}`;
  return `${usd(min)} - ${usd(max)}`;
}

export const usdc = (v: bigint | undefined, digits = 2) =>
  v === undefined ? "-" : Number(formatUnits(v, 6)).toLocaleString(undefined, { maximumFractionDigits: digits });

export const short = (a?: string, n = 4) => (a ? `${a.slice(0, 2 + n)}…${a.slice(-n)}` : "");

export function countdown(secondsLeft: number): string {
  if (secondsLeft <= 0) return "passed";
  const d = Math.floor(secondsLeft / 86400);
  const h = Math.floor((secondsLeft % 86400) / 3600);
  const m = Math.floor((secondsLeft % 3600) / 60);
  const s = Math.floor(secondsLeft % 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m ${s}s`;
}

export const pct = (x: number) => `${Math.round(x * 100)}`;

/** Milestone descriptions are either an IPFS CID (created in the app) or short plain text (seed script). */
export const looksLikeCid = (s: string) => /^(Qm[1-9A-HJ-NP-Za-km-z]{44}|b[a-z2-7]{50,})$/.test(s);
