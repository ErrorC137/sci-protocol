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
          <span className="figure text-2xl font-semibold text-charcoal">{Math.round(total * 100)}</span>
          <span className="text-[10px] uppercase tracking-wide text-charcoal-muted">fit</span>
          <span className="mt-1 text-xs text-charcoal-muted">#{rank}</span>
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          <div>
            <p className="text-xs font-medium text-charcoal-muted">{g.funder_name}</p>
            <h2 className="font-semibold text-charcoal">{g.title}</h2>
          </div>
          <GrantMeta g={g} />
          <div className="rounded-lg bg-limestone-50 p-3 text-sm">
            {exp ? (
              <>
                <p className="text-charcoal"><span className="font-semibold">Why this matched: </span>{exp.why_matched}</p>
                <p className="mt-1 text-charcoal-soft"><span className="font-semibold text-charcoal">To strengthen: </span>{exp.strengthen}</p>
                <p className="mt-1 text-[11px] text-charcoal-muted">{exp.source === "llm" ? "Written by Claude from the rule results - eligibility was decided by the rules, not the model." : "Rule-based explanation (LLM not configured)."}</p>
              </>
            ) : explaining ? (
              <p className="flex items-center gap-2 text-charcoal-muted"><Spinner /> Writing the explanation…</p>
            ) : (
              <p className="text-charcoal-muted">Explanations are generated for the top 10 only.</p>
            )}
          </div>
          {m.warnings.length > 0 && (
            <ul className="space-y-0.5 text-xs text-copper-700">{m.warnings.map((w) => <li key={w}>⚠ {w}</li>)}</ul>
          )}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 pt-1">
            <Deadline g={g} />
            {m.effort.hours_low !== undefined && (
              <span className="text-sm text-charcoal-muted">Effort ~{m.effort.hours_low}-{m.effort.hours_high} h <span className="text-xs">({m.effort.basis})</span></span>
            )}
            <div className="ml-auto flex items-center gap-2">
              <button className="text-sm text-charcoal-muted hover:underline" onClick={() => setOpen(!open)}>{open ? "Hide" : "Show"} details</button>
              {g.url && <a className="text-sm text-charcoal-muted hover:underline" href={g.url} target="_blank" rel="noreferrer">Source ↗</a>}
              {m.effort.prefill_available ? <Button href={`/apply/${g.id}`}>Start application</Button> : <Button href={`/apply/${g.id}`} variant="secondary">Upload form</Button>}
            </div>
          </div>
          {open && (
            <div className="grid gap-4 border-t border-neutral/70 pt-3 md:grid-cols-2">
              <div>
                <p className="mb-2 text-xs font-semibold uppercase text-charcoal-muted">Hard eligibility (passed)</p>
                <RuleList rules={m.rules} />
              </div>
              <div>
                <p className="mb-2 text-xs font-semibold uppercase text-charcoal-muted">Ranking</p>
                {m.score && <ScoreBars s={m.score} boost={boost * KEYWORD_WEIGHT} />}
                {g.summary && <p className="mt-3 text-xs text-charcoal-soft">{g.summary}</p>}
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

      {res.isLoading && <Card className="flex items-center gap-2 text-charcoal-muted"><Spinner /> Matching across the corpus…</Card>}
      {res.error && <Notice tone="danger">Matching failed: {(res.error as Error).message}</Notice>}

      {d && (
        <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2 text-sm text-charcoal-soft">
              <Chip tone="positive">{d.matches.length} eligible</Chip>
              <span>of {d.corpus_size} opportunities · {d.excluded_count} excluded by hard rules</span>
              {keywords && keywords.length > 0 && <Chip tone="positive" title="Applied in your browser">re-ranked locally with {keywords.length} private keyword{keywords.length > 1 ? "s" : ""}</Chip>}
              {exp.data && <Chip tone={exp.data.llm ? "dark" : "neutral"}>{exp.data.llm ? "explanations by Claude" : "rule-based explanations"}</Chip>}
            </div>
            {d.trl_assessment.consistent === false && <Notice>{d.trl_assessment.note}</Notice>}
            {ranked.map(({ m, boost }, i) => (
              <MatchCard key={m.grant.id} m={m} rank={i + 1} boost={boost} exp={exp.data?.explanations[m.grant.id]} explaining={exp.isLoading && i < 10} />
            ))}
            {ranked.length === 0 && <Empty title="Nothing passes the hard rules yet">See what would unlock funding on the right.</Empty>}
          </div>

          <aside className="space-y-4">
            <Card>
              <p className="font-semibold text-charcoal">Why {d.excluded_count} were excluded</p>
              <ul className="mt-2 space-y-1 text-sm text-charcoal-soft">
                {Object.entries(d.excluded_by_rule).map(([r, n]) => <li key={r} className="flex justify-between"><span>{RULE_NAMES[r] ?? r}</span><span className="tabular-nums">{n}</span></li>)}
              </ul>
              <p className="mt-2 text-xs text-charcoal-muted">One grant can fail several rules.</p>
            </Card>
            {d.unlocks.length > 0 && (
              <Card>
                <p className="font-semibold text-charcoal">What would unlock more funding</p>
                <ul className="mt-2 space-y-3">
                  {d.unlocks.map((u) => (
                    <li key={u.change} className="text-sm">
                      <p className="flex justify-between font-medium text-charcoal"><span>{u.label}</span><Chip tone="info">+{u.count}</Chip></p>
                      <p className="text-xs text-charcoal-muted">{u.examples.join(" · ")}</p>
                    </li>
                  ))}
                </ul>
              </Card>
            )}
            {d.near_misses.length > 0 && (
              <Card>
                <p className="font-semibold text-charcoal">Near misses</p>
                <p className="text-xs text-charcoal-muted">Fail exactly one rule.</p>
                <ul className="mt-2 space-y-2 text-sm">
                  {d.near_misses.slice(0, 6).map((m) => (
                    <li key={m.grant.id}>
                      <p className="font-medium text-charcoal">{m.grant.title}</p>
                      <p className="text-xs text-error">{m.rules.find((r) => r.status === "fail")?.detail}</p>
                    </li>
                  ))}
                </ul>
              </Card>
            )}
            <Card tone="dark">
              <p className="font-display font-semibold text-lime">Too early for most of these?</p>
              <p className="mt-1 text-sm text-limestone-300">
                Open a milestone-gated raise: funders’ money sits in escrow and is released only when an attestor approves
                your evidence. Miss a milestone and they get it back.
              </p>
              <div className="mt-3"><Button href="/raise/new">Raise on-chain (testnet)</Button></div>
            </Card>
            <p className="px-1 text-xs text-charcoal-muted">
              Embedder: {d.embedder}. Edit your <Link href="/profile" className="underline">profile</Link> to re-run.
            </p>
          </aside>
        </div>
      )}
    </div>
  );
}
