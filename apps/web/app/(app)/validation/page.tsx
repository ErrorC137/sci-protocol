"use client";

import type { ChainEvent } from "@sci/shared";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, CircleSlash, FileUp, Coins, ShieldCheck, TimerOff, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { FootNote, LiveBadge, SectionTitle } from "@/components/uplo";
import { Card, Chip, Empty, Notice, PageHeader, Spinner, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { DEPLOYMENT, TARGET_CHAIN, addressUrl, txUrl } from "@/lib/chain";
import { short, usdc } from "@/lib/format";
import { useMetadata, useProjects } from "@/lib/hooks";

// Validation = the scientific-milestone record: evidence in, attestor decision, then release or refund.
// Everything here is read from real testnet events (via the API's chain indexer); nothing is simulated.

const STEP: Record<string, { label: string; icon: LucideIcon; cls: string }> = {
  EvidenceSubmitted: { label: "Evidence submitted", icon: FileUp, cls: "bg-white text-charcoal ring-1 ring-inset ring-charcoal/25" },
  Attested: { label: "Attestation recorded", icon: ShieldCheck, cls: "bg-sage-50 text-sage-700 ring-1 ring-inset ring-sage-200" },
  MilestoneApproved: { label: "Approved", icon: CheckCircle2, cls: "bg-lime text-charcoal" },
  MilestoneRejected: { label: "Rejected", icon: CircleSlash, cls: "bg-error-50 text-error-700 ring-1 ring-inset ring-error-200" },
  MilestoneReleased: { label: "Funds released", icon: Coins, cls: "bg-charcoal text-limestone-50" },
  ProjectFailed: { label: "Deadline missed · refunds open", icon: TimerOff, cls: "bg-copper-50 text-copper-700 ring-1 ring-inset ring-copper-200" },
};

const big = (v: unknown) => { try { return BigInt(String(v)); } catch { return 0n; } };
const str = (v: unknown) => (v === undefined || v === null ? "" : String(v));

interface Record_ { projectId: string; index: string; events: ChainEvent[] }

function group(events: ChainEvent[]): Record_[] {
  const map = new Map<string, Record_>();
  for (const e of events) {
    if (!STEP[e.event]) continue;
    const projectId = str(e.args.projectId);
    const index = str(e.event === "ProjectFailed" ? e.args.missedIndex : e.args.index);
    const key = `${projectId}:${index}`;
    if (!map.has(key)) map.set(key, { projectId, index, events: [] });
    map.get(key)!.events.push(e);
  }
  const recs = [...map.values()];
  for (const r of recs) r.events.sort((a, b) => a.block - b.block || a.log_index - b.log_index);
  // newest activity first
  return recs.sort((a, b) => b.events[b.events.length - 1].block - a.events[a.events.length - 1].block);
}

function Detail({ e }: { e: ChainEvent }) {
  const a = e.args;
  const cid = str(a.evidenceCID || a.reasonCID);
  return (
    <span className="text-xs text-charcoal-muted">
      {e.event === "MilestoneReleased" && <>{usdc(big(a.amount), 0)} mUSDC to {short(str(a.researcher))} · </>}
      {e.event === "ProjectFailed" && <>{usdc(big(a.refundPot), 0)} mUSDC refundable · </>}
      {(e.event === "MilestoneApproved" || e.event === "MilestoneRejected" || e.event === "Attested") && a.attestor !== undefined && (
        <>attestor {addressUrl(str(a.attestor)) ? <a className="underline" href={addressUrl(str(a.attestor))} target="_blank" rel="noreferrer">{short(str(a.attestor))}</a> : short(str(a.attestor))} · </>
      )}
      {cid && <><a className="underline" href={api.ipfsUrl(cid)} target="_blank" rel="noreferrer">{e.event === "MilestoneRejected" ? "reason" : "evidence"} {short(cid, 6)}</a> · </>}
      {txUrl(e.tx) ? <a className="underline" href={txUrl(e.tx)} target="_blank" rel="noreferrer">block {e.block}</a> : <>block {e.block}</>}
    </span>
  );
}

function ProjectName({ id, cids }: { id: string; cids: Map<string, string> }) {
  const meta = useMetadata(cids.get(id));
  return <>{meta.data?.nickname ?? `Project #${id}`}</>;
}

function RecordCard({ r, cids }: { r: Record_; cids: Map<string, string> }) {
  const last = r.events[r.events.length - 1].event;
  const outcome = last === "MilestoneReleased" ? <Chip tone="dark">Completed</Chip>
    : last === "MilestoneApproved" ? <Chip tone="positive">Approved</Chip>
    : last === "MilestoneRejected" ? <Chip tone="danger">Needs new evidence</Chip>
    : last === "ProjectFailed" ? <Chip tone="caution">Refunding</Chip>
    : <Chip tone="info">Awaiting attestor</Chip>;
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs text-charcoal-muted">Project #{r.projectId} · Milestone {Number(r.index) + 1}</p>
          <Link href={`/raise/${r.projectId}`} className="font-display font-semibold text-charcoal underline-offset-2 hover:underline">
            <ProjectName id={r.projectId} cids={cids} />
          </Link>
        </div>
        {outcome}
      </div>
      <ol className="mt-4 space-y-3 border-l border-neutral pl-4">
        {r.events.map((e) => {
          const s = STEP[e.event];
          return (
            <li key={`${e.tx}:${e.log_index}`} className="relative">
              <span aria-hidden className="absolute -left-[1.3rem] top-1.5 h-2 w-2 rounded-full bg-charcoal" />
              <span className={cx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold", s.cls)}>
                <s.icon aria-hidden className="h-3 w-3" />{s.label}
              </span>
              <div className="mt-1"><Detail e={e} /></div>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}

export default function Validation() {
  const activity = useQuery({
    queryKey: ["all-activity"], queryFn: () => api.allActivity(500), enabled: !!DEPLOYMENT, retry: false, refetchInterval: 15_000,
  });
  const projects = useProjects();
  const cids = new Map((projects.data ?? []).map((p) => [p.id.toString(), p.metadataCID]));
  const records = activity.data ? group(activity.data.events) : [];

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Validation" title="Scientific milestones, verified before money moves">
        Each research milestone needs evidence. An attestor approves or rejects it on-chain, and only an approved
        milestone releases its tranche from escrow. If a deadline passes without approval, backers can reclaim
        everything that was never released.
      </PageHeader>

      <div className="grid gap-4 md:grid-cols-3">
        {[
          ["01", "Evidence", "The researcher pins evidence to IPFS and submits its content id for the current milestone."],
          ["02", "Attestation", "An attestor reviews it and approves or rejects on-chain. Rejections carry a reason."],
          ["03", "Release or refund", "Approval releases that milestone's funds. A missed deadline opens pro-rata refunds."],
        ].map(([n, t, b]) => (
          <Card key={n}>
            <p className="figure text-sm font-semibold text-copper-700">{n}</p>
            <p className="mt-1 font-display font-semibold text-charcoal">{t}</p>
            <p className="mt-1 text-sm text-charcoal-soft">{b}</p>
          </Card>
        ))}
      </div>

      <section>
        <SectionTitle eyebrow={`On-chain · ${TARGET_CHAIN.name}`} title="Verification records" aside={<LiveBadge>Live testnet events</LiveBadge>} />
        {!DEPLOYMENT && (
          <Notice tone="danger">No contracts deployed on {TARGET_CHAIN.name} yet. Deploy them on the <Link className="underline" href="/setup">setup page</Link>; verification records appear here as soon as milestones are submitted.</Notice>
        )}
        {DEPLOYMENT && activity.isLoading && <Card className="flex items-center gap-2 text-charcoal-muted"><Spinner /> Reading verification records…</Card>}
        {DEPLOYMENT && activity.error && (
          <Notice tone="caution">
            The API&apos;s chain indexer isn&apos;t available right now ({(activity.error as Error).message}). Milestone status is still
            readable on each raise: open one from the <Link className="underline" href="/raise">Innovation Pool</Link>.
          </Notice>
        )}
        {activity.data && records.length === 0 && (
          <Empty title="No verification records yet">Records appear when a researcher submits milestone evidence on a raise.</Empty>
        )}
        <div className="grid gap-4 lg:grid-cols-2">
          {records.map((r) => <RecordCard key={`${r.projectId}:${r.index}`} r={r} cids={cids} />)}
        </div>
      </section>

      <FootNote>
        Testnet demo with a mock stablecoin. The attestor is a single, centralized role today; independent or
        multi-party attestation is future work.
      </FootNote>
    </div>
  );
}
