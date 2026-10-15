"use client";

import { FundingPoolAbi, ProjectRegistryAbi, type ProjectMetadata } from "@sci/shared";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { createPublicClient, http } from "viem";
import { Chip } from "@/components/ui";
import { api } from "@/lib/api";
import { DEPLOYMENT, PROJECT_STATUS, RPC, TARGET_CHAIN } from "@/lib/chain-meta";
import { usdc } from "@/lib/format";
import { CardShell, Progress } from "./Pipeline";

// Live on-chain raises for the landing pipeline. Loaded only when the section approaches the viewport, and reads
// the chain with a bare viem client - no wallet stack - so the landing stays light.

interface Live { id: bigint; metadataCID: string; trl: number; status: number; target: bigint; raised: bigint }

const client = createPublicClient({ chain: TARGET_CHAIN, transport: http(RPC) });

async function fetchProjects(): Promise<Live[]> {
  if (!DEPLOYMENT) return [];
  const n = Number(await client.readContract({ address: DEPLOYMENT.ProjectRegistry, abi: ProjectRegistryAbi, functionName: "projectCount" }));
  const ids = Array.from({ length: Math.min(n, 6) }, (_, i) => BigInt(n - i));
  return Promise.all(ids.map(async (id) => {
    const [p, camp] = await Promise.all([
      client.readContract({ address: DEPLOYMENT!.ProjectRegistry, abi: ProjectRegistryAbi, functionName: "getProject", args: [id] }) as Promise<{ metadataCID: string; trl: number | bigint; status: number | bigint }>,
      client.readContract({ address: DEPLOYMENT!.FundingPool, abi: FundingPoolAbi, functionName: "campaigns", args: [id] }) as Promise<readonly [bigint, bigint, ...unknown[]]>,
    ]);
    return { id, metadataCID: p.metadataCID, trl: Number(p.trl), status: Number(p.status), target: camp[0], raised: camp[1] };
  }));
}

function LiveCard({ p }: { p: Live }) {
  const meta = useQuery({ queryKey: ["ipfs", p.metadataCID], staleTime: Infinity, queryFn: () => api.ipfsJson<ProjectMetadata>(p.metadataCID) });
  return (
    <CardShell art={(["lattice", "crystal", "flow"] as const)[Number(p.id % 3n)]} href={`/raise/${p.id}`}>
      <div className="flex flex-wrap gap-1.5"><Chip tone="dark">Live on testnet</Chip><Chip>TRL {p.trl}</Chip><Chip tone="info">{PROJECT_STATUS[p.status]}</Chip></div>
      <h3 className="font-display text-lg font-semibold text-charcoal">{meta.data?.nickname ?? `Project #${p.id}`}</h3>
      <Progress raised={Number(p.raised) / 1e6} target={Number(p.target) / 1e6} label={`${usdc(p.raised, 0)} / ${usdc(p.target, 0)} mUSDC`} />
    </CardShell>
  );
}

function Cards() {
  const q = useQuery({ queryKey: ["landing-projects", TARGET_CHAIN.id], queryFn: fetchProjects, retry: 1, staleTime: 30_000 });
  return <>{q.data?.filter((p) => p.target > 0n).slice(0, 4).map((p) => <LiveCard key={p.id.toString()} p={p} />)}</>;
}

export default function PipelineLive() {
  const [qc] = useState(() => new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false } } }));
  return <QueryClientProvider client={qc}><Cards /></QueryClientProvider>;
}
