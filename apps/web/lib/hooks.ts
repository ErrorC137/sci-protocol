"use client";

import type { ProjectMetadata } from "@sci/shared";
import { useQuery } from "@tanstack/react-query";
import { keccak256, toBytes, zeroAddress, type Address } from "viem";
import { useAccount, usePublicClient } from "wagmi";
import { api } from "./api";
import { TARGET_CHAIN, contracts } from "./chain";

export const ATTESTOR_ROLE = keccak256(toBytes("ATTESTOR_ROLE"));

export interface Milestone {
  descriptionCID: string;
  amount: bigint;
  deadline: bigint;
  state: number;
  evidenceCID: string;
}

export interface ProjectState {
  researcher: Address;
  metadataCID: string;
  privateDetailHash: `0x${string}`;
  trl: number;
  status: number;
  createdAt: bigint;
  campaign: { target: bigint; raised: bigint; deadline: bigint; finalized: boolean; exists: boolean };
  ledger: { budget: bigint; deposited: bigint; poolDeposited: bigint; released: bigint; refundPot: bigint; refunded: bigint; failed: boolean };
  milestones: Milestone[];
  current: number;
  refundable: boolean;
  raiseFailed: boolean;
  chainNow: number;
  me?: {
    address: Address;
    usdc: bigint;
    allowancePool: bigint;
    contribution: bigint;
    withdrawn: boolean;
    refundableAmount: bigint;
    refundClaimed: boolean;
    fractionsClaimed: boolean;
    fractions: bigint;
    revenue: bigint;
    isAttestor: boolean;
    isResearcher: boolean;
  };
}

/** All contract state a campaign page needs, polled every few seconds (cheap on a testnet). */
export function useProject(pid: bigint | undefined) {
  const client = usePublicClient({ chainId: TARGET_CHAIN.id });
  const { address } = useAccount();
  const c = contracts();
  return useQuery({
    queryKey: ["project", TARGET_CHAIN.id, pid?.toString(), address],
    enabled: !!client && !!c && pid !== undefined,
    refetchInterval: 4000,
    queryFn: async (): Promise<ProjectState> => {
      const r = (fn: string, ct: { address: Address; abi: any }, args: unknown[]) =>
        client!.readContract({ address: ct.address, abi: ct.abi, functionName: fn, args } as any) as Promise<any>;
      const [p, camp, led, ms, cur, refundable, raiseFailed, block] = await Promise.all([
        r("getProject", c!.registry, [pid]),
        r("campaigns", c!.pool, [pid]),
        r("ledgers", c!.escrow, [pid]),
        r("getMilestones", c!.escrow, [pid]),
        r("currentMilestone", c!.escrow, [pid]),
        r("isRefundable", c!.escrow, [pid]),
        r("isFailed", c!.pool, [pid]),
        client!.getBlock({ blockTag: "latest" }),
      ]);
      const state: ProjectState = {
        researcher: p.researcher, metadataCID: p.metadataCID, privateDetailHash: p.privateDetailHash, trl: Number(p.trl),
        status: Number(p.status), createdAt: p.createdAt,
        campaign: { target: camp[0], raised: camp[1], deadline: camp[2], finalized: camp[3], exists: camp[4] },
        ledger: { budget: led[0], deposited: led[1], poolDeposited: led[2], released: led[3], refundPot: led[4], refunded: led[5], failed: led[6] },
        milestones: (ms as any[]).map((m) => ({ descriptionCID: m.descriptionCID, amount: m.amount, deadline: m.deadline, state: Number(m.state), evidenceCID: m.evidenceCID })),
        current: Number(cur),
        refundable,
        raiseFailed,
        chainNow: Number(block.timestamp),
      };
      if (address) {
        const [usdc, allowance, contribution, withdrawn, refundAmt, refundClaimed, fracClaimed, fractions, revenue, isAttestor] = await Promise.all([
          r("balanceOf", c!.usdc, [address]),
          r("allowance", c!.usdc, [address, c!.pool.address]),
          r("contributionOf", c!.pool, [pid, address]),
          r("withdrawn", c!.pool, [pid, address]),
          r("refundableOf", c!.escrow, [pid, address]),
          r("refundClaimed", c!.escrow, [pid, address]),
          r("fractionsClaimed", c!.pool, [pid, address]),
          r("balanceOf", c!.fractions, [address, pid]),
          r("withdrawableRevenueOf", c!.fractions, [pid, address]),
          r("hasRole", c!.escrow, [ATTESTOR_ROLE, address]),
        ]);
        state.me = {
          address, usdc, allowancePool: allowance, contribution, withdrawn, refundableAmount: refundAmt, refundClaimed,
          fractionsClaimed: fracClaimed, fractions, revenue, isAttestor,
          isResearcher: p.researcher.toLowerCase() === address.toLowerCase(),
        };
      }
      return state;
    },
  });
}

export interface ProjectSummary {
  id: bigint;
  researcher: Address;
  metadataCID: string;
  trl: number;
  status: number;
  target: bigint;
  raised: bigint;
}

export function useProjects() {
  const client = usePublicClient({ chainId: TARGET_CHAIN.id });
  const c = contracts();
  return useQuery({
    queryKey: ["projects", TARGET_CHAIN.id],
    enabled: !!client && !!c,
    refetchInterval: 8000,
    queryFn: async (): Promise<ProjectSummary[]> => {
      const r = (fn: string, ct: { address: Address; abi: any }, args: unknown[]) =>
        client!.readContract({ address: ct.address, abi: ct.abi, functionName: fn, args } as any) as Promise<any>;
      const n = Number(await r("projectCount", c!.registry, []));
      const ids = Array.from({ length: n }, (_, i) => BigInt(n - i));
      return Promise.all(ids.map(async (id) => {
        const [p, camp] = await Promise.all([r("getProject", c!.registry, [id]), r("campaigns", c!.pool, [id])]);
        return { id, researcher: p.researcher, metadataCID: p.metadataCID, trl: Number(p.trl), status: Number(p.status), target: camp[0], raised: camp[1] };
      }));
    },
  });
}

export function useMetadata(cid: string | undefined) {
  return useQuery({
    queryKey: ["ipfs", cid],
    enabled: !!cid,
    staleTime: Infinity,
    queryFn: () => api.ipfsJson<ProjectMetadata>(cid!),
  });
}

export const isZeroHash = (h?: string) => !h || /^0x0+$/.test(h);
export const isZeroAddress = (a?: string) => !a || a === zeroAddress;
