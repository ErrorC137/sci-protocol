"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { CapitalFlowDiagram, DemoBadge, FootNote, KpiTile, LiveBadge, SectionTitle, compactMoney } from "@/components/uplo";
import { Card, Chip, PageHeader, StatusChip } from "@/components/ui";
import { api } from "@/lib/api";
import { DEPLOYMENT, PROJECT_STATUS, TARGET_CHAIN } from "@/lib/chain";
import { usdc } from "@/lib/format";
import { useMetadata, useProjects, type ProjectSummary } from "@/lib/hooks";
import { DEMO_KPIS, DEMO_OPPORTUNITIES, WATERFALL } from "@/lib/uplo-demo-data";

const th = "px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-eyebrow text-charcoal-muted";
const td = "px-4 py-3 align-middle";

function demoStatus(s: (typeof DEMO_OPPORTUNITIES)[number]["status"]) {
  if (s === "In Progress") return <span className="inline-flex rounded-full bg-limestone-200 px-2.5 py-0.5 text-xs font-semibold text-charcoal ring-1 ring-inset ring-neutral">In Progress</span>;
  if (s === "Funding") return <span className="inline-flex rounded-full bg-lime px-2.5 py-0.5 text-xs font-semibold text-charcoal">Funding</span>;
  return <span className="inline-flex rounded-full bg-white px-2.5 py-0.5 text-xs font-semibold text-charcoal ring-1 ring-inset ring-charcoal/30">Open</span>;
}

function LiveRow({ p }: { p: ProjectSummary }) {
  const meta = useMetadata(p.metadataCID);
  return (
    <tr className="border-t border-neutral">
      <td className={td}>
        <Link href={`/raise/${p.id}`} className="font-semibold text-charcoal underline-offset-2 hover:underline">
          {meta.data?.nickname ?? `Project #${p.id}`}
        </Link>
        <div className="mt-1"><LiveBadge>On-chain</LiveBadge></div>
      </td>
      <td className={td}>{meta.data?.subdomains?.[0] ?? "Research raise"}</td>
      <td className={td}><Chip>TRL {p.trl}</Chip></td>
      <td className={`${td} figure`}>{p.target > 0n ? `${usdc(p.target, 0)} mUSDC` : "-"}</td>
      <td className={td}><Chip tone={p.status === 4 ? "danger" : p.status === 3 ? "dark" : "info"}>{PROJECT_STATUS[p.status]}</Chip></td>
      <td className={`${td} text-charcoal-muted`}>Milestone-gated</td>
    </tr>
  );
}

export default function Overview() {
  const projects = useProjects();
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 30_000 });
  const live = projects.data ?? [];
  const raised = live.reduce((s, p) => s + p.raised, 0n);
  const releasedEvents = useQuery({
    queryKey: ["all-activity"], queryFn: () => api.allActivity(500), enabled: !!DEPLOYMENT, retry: false, refetchInterval: 15_000,
  });
  const approvals = releasedEvents.data?.events.filter((e) => e.event === "MilestoneApproved").length;

  return (
    <div className="space-y-10">
      <PageHeader title="Overview">
        Real industry value. Real innovation. Commercial assets are financed today, part of the platform margin funds
        tomorrow&apos;s research, and research money is released milestone by milestone.
      </PageHeader>

      <section>
        <SectionTitle eyebrow="Platform" title="Key figures" aside={<DemoBadge />} />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiTile label="Verified Assets" value={compactMoney(DEMO_KPIS.verifiedAssets.value)} trend={DEMO_KPIS.verifiedAssets.delta} bars={DEMO_KPIS.verifiedAssets.bars} tone="copper" badge={<DemoBadge>Demo</DemoBadge>} />
          <KpiTile label="Active Financing" value={compactMoney(DEMO_KPIS.activeFinancing.value)} trend={DEMO_KPIS.activeFinancing.delta} bars={DEMO_KPIS.activeFinancing.bars} tone="neutral" badge={<DemoBadge>Demo</DemoBadge>} />
          <KpiTile label="Innovation Capital" value={compactMoney(DEMO_KPIS.innovationCapital.value)} trend={DEMO_KPIS.innovationCapital.delta} bars={DEMO_KPIS.innovationCapital.bars} tone="lime" badge={<DemoBadge>Demo</DemoBadge>} />
          <KpiTile label="Research Projects" value={DEMO_KPIS.researchProjects.value} sub={DEMO_KPIS.researchProjects.delta} bars={DEMO_KPIS.researchProjects.bars} tone="copper" badge={<DemoBadge>Demo</DemoBadge>} />
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiTile label="On-chain raises" badge={<LiveBadge />}
            value={DEPLOYMENT ? (projects.isLoading ? "…" : live.length) : "-"}
            sub={DEPLOYMENT ? `Innovation Pool on ${TARGET_CHAIN.name}` : <>Contracts not deployed · <Link href="/setup" className="underline">setup</Link></>} />
          <KpiTile label="Escrowed for research" badge={<LiveBadge />}
            value={DEPLOYMENT ? `${usdc(raised, 0)}` : "-"} sub="mUSDC raised into milestone escrow (testnet, no real value)" />
          <KpiTile label="Milestones approved" badge={<LiveBadge />}
            value={approvals ?? "-"} sub={approvals === undefined ? "Needs the API's chain indexer" : "Attested on-chain"} />
          <KpiTile label="Funding routes indexed" badge={<LiveBadge />}
            value={health.data?.corpus_size ?? "…"} sub="Grants and programmes in the Research Pipeline" />
        </div>
      </section>

      <section>
        <Card className="p-6">
          <SectionTitle eyebrow="How money moves" title="Capital flow" aside={<Link href="/commercial-finance" className="inline-flex items-center gap-1 text-sm font-semibold text-charcoal underline-offset-2 hover:underline">See the invoice waterfall <ArrowRight aria-hidden className="h-4 w-4" /></Link>} />
          <CapitalFlowDiagram />
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-neutral border-l-4 border-l-copper p-4">
              <p className="eyebrow">Pool A · Commercial Financing</p>
              <p className="mt-1 text-sm text-charcoal-soft">Working capital for recyclers with verifiable transactions. Investor principal and returns stay here.</p>
            </div>
            <div className="rounded-lg border border-neutral border-l-4 border-l-lime-500 p-4">
              <p className="eyebrow">Pool B · Innovation Treasury</p>
              <p className="mt-1 text-sm text-charcoal-soft">Allocated platform revenue, corporate R&amp;D partners and risk-accepting backers fund TRL 4–6 research.</p>
            </div>
          </div>
          <FootNote>
            Investor principal in commercial financing is never used for research. In the illustrative $100,000 invoice,
            the platform fee is {compactMoney(WATERFALL.platformFee)} and {compactMoney(WATERFALL.treasury)} of the margin goes to Pool B.
          </FootNote>
        </Card>
      </section>

      <section>
        <SectionTitle eyebrow="Research Pipeline" title="Active opportunities"
          aside={<Link href="/raise" className="inline-flex items-center gap-1 text-sm font-semibold text-charcoal underline-offset-2 hover:underline">View All <ArrowRight aria-hidden className="h-4 w-4" /></Link>} />
        <div className="overflow-x-auto rounded-xl border border-neutral bg-white">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="bg-limestone-50">
              <tr><th className={th}>Project</th><th className={th}>Type</th><th className={th}>TRL</th><th className={th}>Funding target</th><th className={th}>Status</th><th className={th}>Expected impact</th></tr>
            </thead>
            <tbody>
              {live.map((p) => <LiveRow key={p.id.toString()} p={p} />)}
              {DEMO_OPPORTUNITIES.map((d) => (
                <tr key={d.title} className="border-t border-neutral">
                  <td className={td}><span className="font-semibold text-charcoal">{d.title}</span><div className="mt-1"><DemoBadge>Demo</DemoBadge></div></td>
                  <td className={td}>{d.type}</td>
                  <td className={td}><Chip>TRL {d.trl}</Chip></td>
                  <td className={`${td} figure`}>{compactMoney(d.target)}</td>
                  <td className={td}>{demoStatus(d.status)}</td>
                  <td className={`${td} text-charcoal-soft`}>{d.impact}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <FootNote>Rows marked On-chain are live testnet raises (mock stablecoin, no real value). Rows marked Demo are simulated examples.</FootNote>
      </section>
    </div>
  );
}
