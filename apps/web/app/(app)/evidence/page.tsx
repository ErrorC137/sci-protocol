"use client";

import type { EvidenceJudgment, EvidenceReport, EvidenceSubmission } from "@sci/shared";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Card, Chip, Label, Notice, PageHeader, Spinner, Toggle, cx, inputCls } from "@/components/ui";
import { api } from "@/lib/api";

const STATE_TONE = { ok: "positive", empty: "neutral", error: "danger", no_key: "caution", disabled: "neutral", unreachable: "danger" } as const;
const VERDICT = {
  disclosed: { tone: "bg-error-100 text-error-700", label: "disclosed" },
  partial: { tone: "bg-copper-100 text-copper-700", label: "partial" },
  absent: { tone: "bg-lime-50 text-lime-800", label: "absent" },
  unsupported: { tone: "bg-limestone-100 text-charcoal-muted line-through", label: "quote failed" },
} as const;
const SIGNAL = {
  disclosed_before_priority: ["danger", "disclosed before priority date"],
  disclosed_date_unknown: ["caution", "disclosed (date unknown)"],
  partially_disclosed: ["caution", "partially disclosed"],
  not_found_in_retrieved: ["positive", "not found in retrieved set"],
} as const;

const EXAMPLE: EvidenceSubmission = {
  title: "Hydrothermal relithiation of spent NMC811 cathodes",
  abstract: "Spent LiNi0.8Mn0.1Co0.1O2 cathode powder was separated from aluminium foil and relithiated in 2.5 M LiOH at 220 °C for 4 h, followed by annealing at 850 °C in oxygen. The regenerated NMC811 delivered 192 mAh/g at 0.1 C in CR2032 coin cells and retained 91% capacity after 200 cycles.",
  claims: "", methods: "", keywords: ["hydrothermal relithiation", "spent NMC cathode", "direct regeneration"],
  priority_date: "", confidential: true, allow_llm: true,
};

function Cell({ j, onPick, active }: { j?: EvidenceJudgment; onPick: () => void; active: boolean }) {
  if (!j) return <td className="border border-neutral px-2 py-1 text-center text-xs text-charcoal-dim">-</td>;
  const v = VERDICT[j.verdict];
  return (
    <td className="border border-neutral p-0">
      <button onClick={onPick} title={j.quote ?? j.rationale ?? ""}
        className={cx("w-full px-2 py-1 text-xs font-medium", v.tone, active && "ring-2 ring-charcoal ring-inset")}>
        {v.label}{j.method === "lexical" && j.verdict !== "absent" ? "*" : ""}
      </button>
    </td>
  );
}

function Report({ r }: { r: EvidenceReport }) {
  const [pick, setPick] = useState<EvidenceJudgment | null>(null);
  const judgedRefs = Array.from(new Set(r.judgments.map((j) => j.ref)));
  const refByKey = Object.fromEntries(r.references.map((x) => [x.key, x]));
  const cell = (el: string, ref: string) => r.judgments.find((j) => j.element === el && j.ref === ref);
  const sig = Object.fromEntries(r.element_signals.map((s) => [s.element, s]));
  return (
    <div className="space-y-6">
      <Notice tone="info">
        <p className="font-semibold">{r.summary}</p>
        <p className="mt-1 text-sm">{r.coverage}</p>
      </Notice>

      <Card className="space-y-2">
        <h3 className="font-semibold text-charcoal">Sources searched</h3>
        <div className="flex flex-wrap gap-2">
          {r.sources.map((s) => (
            <Chip key={s.source} tone={STATE_TONE[s.state]} title={s.detail ?? s.queries.join(" | ")}>
              {s.source}: {s.state}{s.state === "ok" ? ` (${s.hits})` : ""}
            </Chip>
          ))}
        </div>
        <p className="text-xs text-charcoal-muted">Hover a chip for the reason or the exact query sent. Sources marked no_key / unreachable were NOT searched; their absence lowers recall.</p>
      </Card>

      <Card className="space-y-3 overflow-x-auto">
        <h3 className="font-semibold text-charcoal">Claim chart: your elements vs prior art</h3>
        {r.elements.length === 0 ? <p className="text-sm text-charcoal-soft">No elements could be extracted.</p> : judgedRefs.length === 0 ? (
          <p className="text-sm text-charcoal-soft">No references were retrieved, so nothing could be compared. See the sources above.</p>
        ) : (
          <table className="min-w-full border-collapse text-left text-sm">
            <thead>
              <tr>
                <th className="border border-neutral px-2 py-1 text-xs text-charcoal-muted">Element</th>
                <th className="border border-neutral px-2 py-1 text-xs text-charcoal-muted">Signal</th>
                {judgedRefs.map((k) => (
                  <th key={k} className="border border-neutral px-2 py-1 text-xs font-mono text-charcoal-muted" title={refByKey[k]?.title}>
                    {k.replace(/^(pat|doi|arxiv|openalex|s2):/, "")}{refByKey[k]?.fixture ? " (TEST)" : ""}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {r.elements.map((e) => (
                <tr key={e.id}>
                  <td className="max-w-md border border-neutral px-2 py-1 align-top text-xs"><span className="font-mono font-semibold">{e.id}</span> {e.text}</td>
                  <td className="border border-neutral px-2 py-1 align-top">
                    {sig[e.id] && <Chip tone={SIGNAL[sig[e.id].status][0]}>{SIGNAL[sig[e.id].status][1]}</Chip>}
                  </td>
                  {judgedRefs.map((k) => {
                    const j = cell(e.id, k);
                    return <Cell key={k} j={j} active={pick === j} onPick={() => setPick(j ?? null)} />;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {pick && (
          <div className="rounded-lg border border-neutral bg-limestone-50 p-3 text-sm">
            <p className="font-semibold">{pick.element} vs {pick.ref} — {VERDICT[pick.verdict].label} ({pick.method})</p>
            {pick.quote && <blockquote className="mt-1 border-l-4 border-lime-500 pl-3 italic">“{pick.quote}”</blockquote>}
            {pick.rationale && <p className="mt-1 text-charcoal-soft">{pick.rationale}</p>}
          </div>
        )}
        <p className="text-xs text-charcoal-muted">
          Every quote was checked to appear verbatim in the reference; judgments whose quote failed are struck through and excluded.
          * = lexical comparison (no LLM): a weak, transparent signal. A patent attorney decides anticipation and obviousness.
        </p>
      </Card>

      <Card className="space-y-2">
        <h3 className="font-semibold text-charcoal">References ({r.references.length})</h3>
        <ul className="divide-y divide-neutral">
          {r.references.map((x) => (
            <li key={x.key} className="py-2 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <Chip tone={x.kind === "patent" ? "dark" : "info"}>{x.kind}</Chip>
                {x.fixture && <Chip tone="danger">TEST FIXTURE</Chip>}
                {x.before_priority === true && <Chip tone="danger">before priority date</Chip>}
                {x.before_priority === null && <Chip tone="neutral">date vs priority unknown</Chip>}
                <span className="font-mono text-xs text-charcoal-muted">{x.key}</span>
                <span className="text-xs text-charcoal-muted">{x.date ?? "no date"} · {x.source}{x.also_in.length ? ` + ${x.also_in.join(", ")}` : ""} · score {x.score.toFixed(2)}</span>
              </div>
              <p className="mt-0.5 font-medium">{x.url ? <a className="underline" href={x.url} target="_blank" rel="noreferrer">{x.title}</a> : x.title}</p>
              {x.assignees.length > 0 && <p className="text-xs text-charcoal-muted">{x.assignees.join("; ")}</p>}
            </li>
          ))}
        </ul>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="space-y-2">
          <h3 className="font-semibold text-charcoal">TRL from evidence</h3>
          <p className="text-2xl font-bold">{r.trl.low ? `TRL ${r.trl.low}` : "Not determinable"}</p>
          <p className="text-xs text-charcoal-muted">Track: {r.trl.track.replace(/_/g, " ")} · rubric {r.trl.rubric_version}</p>
          <ul className="space-y-1 text-sm">
            {r.trl.evidence.map((e, i) => (
              <li key={i} className={cx(!e.achieved && "text-charcoal-muted")}>
                <Chip tone={e.achieved ? "positive" : "neutral"}>TRL {e.level} {e.achieved ? "" : "(planned)"}</Chip> {e.cue}: <span className="italic">“{e.quote}”</span>
              </li>
            ))}
          </ul>
          {r.trl.next_milestones.length > 0 && <p className="text-sm"><strong>Next:</strong> {r.trl.next_milestones.join(" ")}</p>}
          <p className="text-xs text-charcoal-muted">{r.trl.note}</p>
        </Card>
        <Card className="space-y-2">
          <h3 className="font-semibold text-charcoal">Freedom-to-operate flags</h3>
          {r.fto_flags.length === 0 ? (
            <p className="text-sm text-charcoal-soft">No retrieved patent claim had every element matched in your described process. Only patents with claim text can be checked; this is not clearance.</p>
          ) : r.fto_flags.map((f) => (
            <div key={f.ref} className="rounded-lg border border-error-200 bg-error-50 p-3 text-sm">
              <p className="font-semibold">{f.ref} · {f.country ?? "?"} · legal status: {f.legal_status}</p>
              <p className="text-charcoal-soft">{f.note}</p>
            </div>
          ))}
        </Card>
      </div>

      {r.dropped_judgments.length > 0 && (
        <Card className="space-y-1">
          <h3 className="font-semibold text-charcoal">Model output rejected by the verifier ({r.dropped_judgments.length})</h3>
          <ul className="list-disc pl-5 text-xs text-charcoal-soft">
            {r.dropped_judgments.map((d, i) => <li key={i}>{String(d.stage)} {String(d.element ?? "")} {String(d.ref ?? "")}: {String(d.reason)}</li>)}
          </ul>
        </Card>
      )}

      <Card className="space-y-1 text-sm">
        <p><strong>Evidence bundle sha256</strong> <span className="break-all font-mono text-xs">{r.bundle_sha256}</span></p>
        <p className="text-xs text-charcoal-muted">
          Deterministic over the report (minus timestamp). An attestor can anchor it in the AttestationRegistry. If the submission is confidential,
          encrypt the bundle before pinning it anywhere public: publishing invention details can destroy patent novelty.
        </p>
        <p className="text-xs text-charcoal-muted">{r.disclaimer} {r.llm_used ? "An LLM was used for extraction/judging." : "No LLM was used."}</p>
      </Card>
    </div>
  );
}

export default function EvidencePage() {
  const [sub, setSub] = useState<EvidenceSubmission>(EXAMPLE);
  const [kw, setKw] = useState(EXAMPLE.keywords.join(", "));
  const sources = useQuery({ queryKey: ["evidence-sources"], queryFn: api.evidenceSources });
  const run = useMutation({
    mutationFn: () => api.assessEvidence({
      ...sub, claims: sub.claims || null, methods: sub.methods || null, priority_date: sub.priority_date || null,
      keywords: kw.split(",").map((s) => s.trim()).filter(Boolean),
    }),
  });
  const set = (k: keyof EvidenceSubmission) => (e: { target: { value: string } }) => setSub({ ...sub, [k]: e.target.value });
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Evidence engine" title="Check research against real patents and literature">
        Elements of your invention are compared with retrieved patents and papers. Every disclosure shown is backed by a quote
        that was checked against the source, and every source that could not be searched is listed.
      </PageHeader>

      <Card className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1 md:col-span-2"><Label>Title</Label><input className={inputCls} value={sub.title} onChange={set("title")} /></div>
          <div className="space-y-1 md:col-span-2"><Label>Abstract</Label><textarea rows={4} className={inputCls} value={sub.abstract} onChange={set("abstract")} /></div>
          <div className="space-y-1"><Label hint="numbered, if a patent application exists">Claims (optional)</Label><textarea rows={4} className={inputCls} value={sub.claims ?? ""} onChange={set("claims")} /></div>
          <div className="space-y-1"><Label hint="scale, cells, feedstock - used for TRL and FTO">Methods / results (optional)</Label><textarea rows={4} className={inputCls} value={sub.methods ?? ""} onChange={set("methods")} /></div>
          <div className="space-y-1"><Label hint="comma separated; the ONLY text sent to external search APIs in confidential mode">Public search keywords</Label><input className={inputCls} value={kw} onChange={(e) => setKw(e.target.value)} /></div>
          <div className="space-y-1"><Label hint="earliest filing or public disclosure">Priority date</Label><input type="date" className={inputCls} value={sub.priority_date ?? ""} onChange={set("priority_date")} /></div>
        </div>
        <div className="flex flex-wrap gap-6">
          <Toggle checked={sub.confidential} onChange={(v) => setSub({ ...sub, confidential: v })}>Confidential (unpublished): keep full text on this server</Toggle>
          <Toggle checked={sub.allow_llm} onChange={(v) => setSub({ ...sub, allow_llm: v })}>Allow the LLM to read the submission</Toggle>
        </div>
        {sources.data && (
          <div className="flex flex-wrap gap-2 text-xs">
            {sources.data.sources.map((s) => <Chip key={s.source} tone={s.configured ? "positive" : "caution"} title={s.detail ?? ""}>{s.source}{s.configured ? "" : ": not configured"}</Chip>)}
          </div>
        )}
        <div className="flex items-center gap-3">
          <Button onClick={() => run.mutate()} disabled={run.isPending || sub.title.length < 3 || sub.abstract.length < 20}>
            {run.isPending && <Spinner />} Run evidence search
          </Button>
          {run.isError && <span className="text-sm text-error">{(run.error as Error).message}</span>}
        </div>
      </Card>

      {run.data && <Report r={run.data} />}
    </div>
  );
}
