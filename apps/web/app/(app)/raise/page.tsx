"use client";

import Link from "next/link";
import { Button, Card, Chip, Empty, Notice, PageHeader, Spinner } from "@/components/ui";
import { DEPLOYMENT, PROJECT_STATUS, TARGET_CHAIN } from "@/lib/chain";
import { short, usdc } from "@/lib/format";
import { useMetadata, useProjects, type ProjectSummary } from "@/lib/hooks";

const STATUS_TONE = ["neutral", "info", "dark", "positive", "danger"] as const;

function ProjectCard({ p }: { p: ProjectSummary }) {
  const meta = useMetadata(p.metadataCID);
  const pct = p.target > 0n ? Number((p.raised * 1000n) / p.target) / 10 : 0;
  return (
    <Link href={`/raise/${p.id}`}>
      <Card className="h-full transition-colors hover:border-charcoal">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs text-charcoal-muted">Project #{p.id.toString()} · {short(p.researcher)}</p>
            <h2 className="font-semibold text-charcoal">{meta.data?.nickname ?? `Project #${p.id}`}</h2>
          </div>
          <Chip tone={STATUS_TONE[p.status]}>{PROJECT_STATUS[p.status]}</Chip>
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Chip>TRL {p.trl}</Chip>
          {meta.data?.subdomains?.slice(0, 2).map((s) => <Chip key={s}>{s}</Chip>)}
        </div>
        {p.target > 0n && (
          <div className="mt-3">
            <div className="h-2 rounded-full bg-charcoal/10"><div className="h-2 rounded-full bg-lime-500" style={{ width: `${Math.min(100, pct)}%` }} /></div>
            <p className="mt-1 text-xs text-charcoal-muted">{usdc(p.raised, 0)} / {usdc(p.target, 0)} mUSDC</p>
          </div>
        )}
      </Card>
    </Link>
  );
}

export default function RaiseList() {
  const projects = useProjects();
  return (
    <div>
      <PageHeader eyebrow={`On-chain · ${TARGET_CHAIN.name}`} title="Milestone-gated raises">
        Funds go into escrow and are released one milestone at a time, only after an attestor approves the evidence.
        If a milestone deadline passes, anyone can trigger a refund and funders pull back what was never released.
      </PageHeader>
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Button href="/raise/new">Open a raise</Button>
        <span className="text-sm text-charcoal-muted">Testnet only · mock USDC · no real value</span>
      </div>
      {!DEPLOYMENT && <Notice tone="danger">No contracts deployed for chain {TARGET_CHAIN.id}. Run the deploy script and `npm run export-abis` (docs/DEPLOY.md).</Notice>}
      {projects.isLoading && <Card className="flex items-center gap-2 text-charcoal-muted"><Spinner /> Reading projects from chain…</Card>}
      {projects.error && <Notice tone="danger">Couldn’t read the chain: {(projects.error as Error).message}</Notice>}
      {projects.data?.length === 0 && <Empty title="No projects yet">Be the first to open a raise.</Empty>}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {projects.data?.map((p) => <ProjectCard key={p.id.toString()} p={p} />)}
      </div>
    </div>
  );
}
