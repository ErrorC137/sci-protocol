"use client";

import type { Explanation, MatchResult } from "@sci/shared";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Deadline, GrantMeta, RuleList, ScoreBars } from "@/components/GrantBits";
import { Button, Card, Chip, Empty, Notice, PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { KEYWORD_WEIGHT, keywordBoost } from "@/lib/keywords";
import { useKeywords, useProfile } from "@/lib/local";

const RULE_NAMES: Record<string, string> = {
  applicant_type: "applicant type", incorporation: "needs a registered company", country: "country", trl: "TRL band",
  equity: "takes equity", amount: "award size", deadline: "closed", ip: "IP assignment",
};

function MatchCard({ m, rank, boost, exp, explaining }: { m: MatchResult; rank: number; boost: number; exp?: Explanation; explaining: boolean }) {
  const [open, setOpen] = useState(false);
  const g = m.grant;
  const total = (m.score?.total ?? 0) + boost * KEYWORD_WEIGHT;
  return (
    <Card className="space-y-3">
      <div className="flex gap-4">
        <div className="flex w-14 shrink-0 flex-col items-center">
          <span className="text-2xl font-bold tabular-nums text-brand-700">{Math.round(total * 100)}</span>
          <span className="text-[10px] uppercase tracking-wide text-ink-muted">fit</span>
          <span className="mt-1 text-xs text-ink-muted">#{rank}</span>
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          <div>
            <p className="text-xs font-medium text-ink-muted">{g.funder_name}</p>
            <h2 className="font-semibold text-ink">{g.title}</h2>
          </div>
          <GrantMeta g={g} />
          <div className="rounded-lg bg-slate-50 p-3 text-sm">
            {exp ? (
              <>
                <p className="text-ink"><span className="font-semibold">Why this matched: </span>{exp.why_matched}</p>
                <p className="mt-1 text-ink-soft"><span className="font-semibold text-ink">To strengthen: </span>{exp.strengthen}</p>
                <p className="mt-1 text-[11px] text-ink-muted">{exp.source === "llm" ? "Written by Claude from the rule results - eligibility was decided by the rules, not the model." : "Rule-based explanation (LLM not configured)."}</p>
              </>
            ) : explaining ? (
              <p className="flex items-center gap-2 text-ink-muted"><Spinner /> Writing the explanation…</p>
            ) : (
              <p className="text-ink-muted">Explanations are generated for the top 10 only.</p>
            )}
          </div>
          {m.warnings.length > 0 && (
            <ul className="space-y-0.5 text-xs text-amber-800">{m.warnings.map((w) => <li key={w}>⚠ {w}</li>)}</ul>
          )}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 pt-1">
            <Deadline g={g} />
            {m.effort.hours_low !== undefined && (
              <span className="text-sm text-ink-muted">Effort ~{m.effort.hours_low}-{m.effort.hours_high} h <span className="text-xs">({m.effort.basis})</span></span>
            )}
            <div className="ml-auto flex items-center gap-2">
              <button className="text-sm text-ink-muted hover:underline" onClick={() => setOpen(!open)}>{open ? "Hide" : "Show"} details</button>
              {g.url && <a className="text-sm text-ink-muted hover:underline" href={g.url} target="_blank" rel="noreferrer">Source ↗</a>}
              {m.effort.prefill_available ? <Button href={`/apply/${g.id}`}>Start application</Button> : <Button href={`/apply/${g.id}`} variant="secondary">Upload form</Button>}
            </div>
          </div>
          {open && (
            <div className="grid gap-4 border-t border-slate-100 pt-3 md:grid-cols-2">
              <div>
                <p className="mb-2 text-xs font-semibold uppercase text-ink-muted">Hard eligibility (passed)</p>
                <RuleList rules={m.rules} />
              </div>
              <div>
                <p className="mb-2 text-xs font-semibold uppercase text-ink-muted">Ranking</p>
                {m.score && <ScoreBars s={m.score} boost={boost * KEYWORD_WEIGHT} />}
                {g.summary && <p className="mt-3 text-xs text-ink-soft">{g.summary}</p>}
              </div>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

export default function Matches() {
  const [profile, , loaded] = useProfile();
  const [keywords] = useKeywords();
  const res = useQuery({
    queryKey: ["match", profile],
    queryFn: () => api.match(profile!),
    enabled: !!profile,
  });

  const ranked = useMemo(() => {
    if (!res.data) return [];
    return res.data.matches
      .map((m) => ({ m, boost: keywordBoost(keywords ?? [], m.grant) }))
      .sort((a, b) => (b.m.score!.total + b.boost * KEYWORD_WEIGHT) - (a.m.score!.total + a.boost * KEYWORD_WEIGHT));
  }, [res.data, keywords]);

  const top = ranked.slice(0, 10).map((r) => r.m.grant.id);
  const exp = useQuery({
    queryKey: ["explain", profile, top],
    queryFn: () => api.explain(profile!, top),
    enabled: !!profile && top.length > 0,
    staleTime: Infinity,
  });

  if (!loaded) return null;
  if (!profile) {
    return <Empty title="No profile yet"><p>Build your non-confidential profile first.</p><div className="mt-4"><Button href="/profile">Start the profile</Button></div></Empty>;
  }

  const d = res.data;
  return (
    <div>
      <PageHeader eyebrow="Matches" title={profile.nickname || "Your matches"}>
        Hard eligibility rules decided what’s on this page. The ranking blends similarity, field overlap, TRL fit, amount fit and
        deadline runway; the explanations only describe what the rules already decided.
      </PageHeader>

      {res.isLoading && <Card className="flex items-center gap-2 text-ink-muted"><Spinner /> Matching across the corpus…</Card>}
      {res.error && <Notice tone="red">Matching failed: {(res.error as Error).message}</Notice>}

      {d && (
        <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2 text-sm text-ink-soft">
              <Chip tone="green">{d.matches.length} eligible</Chip>
              <span>of {d.corpus_size} opportunities · {d.excluded_count} excluded by hard rules</span>
              {keywords && keywords.length > 0 && <Chip tone="green" title="Applied in your browser">re-ranked locally with {keywords.length} private keyword{keywords.length > 1 ? "s" : ""}</Chip>}
              {exp.data && <Chip tone={exp.data.llm ? "violet" : "slate"}>{exp.data.llm ? "explanations by Claude" : "rule-based explanations"}</Chip>}
            </div>
            {d.trl_assessment.consistent === false && <Notice>{d.trl_assessment.note}</Notice>}
            {ranked.map(({ m, boost }, i) => (
              <MatchCard key={m.grant.id} m={m} rank={i + 1} boost={boost} exp={exp.data?.explanations[m.grant.id]} explaining={exp.isLoading && i < 10} />
            ))}
            {ranked.length === 0 && <Empty title="Nothing passes the hard rules yet">See what would unlock funding on the right.</Empty>}
          </div>

          <aside className="space-y-4">
            <Card>
              <p className="font-semibold text-ink">Why {d.excluded_count} were excluded</p>
              <ul className="mt-2 space-y-1 text-sm text-ink-soft">
                {Object.entries(d.excluded_by_rule).map(([r, n]) => <li key={r} className="flex justify-between"><span>{RULE_NAMES[r] ?? r}</span><span className="tabular-nums">{n}</span></li>)}
              </ul>
              <p className="mt-2 text-xs text-ink-muted">One grant can fail several rules.</p>
            </Card>
            {d.unlocks.length > 0 && (
              <Card>
                <p className="font-semibold text-ink">What would unlock more funding</p>
                <ul className="mt-2 space-y-3">
                  {d.unlocks.map((u) => (
                    <li key={u.change} className="text-sm">
                      <p className="flex justify-between font-medium text-ink"><span>{u.label}</span><Chip tone="blue">+{u.count}</Chip></p>
                      <p className="text-xs text-ink-muted">{u.examples.join(" · ")}</p>
                    </li>
                  ))}
                </ul>
              </Card>
            )}
            {d.near_misses.length > 0 && (
              <Card>
                <p className="font-semibold text-ink">Near misses</p>
                <p className="text-xs text-ink-muted">Fail exactly one rule.</p>
                <ul className="mt-2 space-y-2 text-sm">
                  {d.near_misses.slice(0, 6).map((m) => (
                    <li key={m.grant.id}>
                      <p className="font-medium text-ink">{m.grant.title}</p>
                      <p className="text-xs text-rose-700">{m.rules.find((r) => r.status === "fail")?.detail}</p>
                    </li>
                  ))}
                </ul>
              </Card>
            )}
            <Card className="border-brand-100 bg-brand-50">
              <p className="font-semibold text-brand-700">Too early for most of these?</p>
              <p className="mt-1 text-sm text-ink-soft">
                Open a milestone-gated raise: funders’ money sits in escrow and is released only when an attestor approves
                your evidence. Miss a milestone and they get it back.
              </p>
              <div className="mt-3"><Button href="/raise/new">Raise on-chain (testnet)</Button></div>
            </Card>
            <p className="px-1 text-xs text-ink-muted">
              Embedder: {d.embedder}. Edit your <Link href="/profile" className="underline">profile</Link> to re-run.
            </p>
          </aside>
        </div>
      )}
    </div>
  );
}
