"use client";

import type { ProjectMetadata } from "@sci/shared";
import { useConnectModal } from "@rainbow-me/rainbowkit";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { decodeEventLog, parseUnits } from "viem";
import { useAccount, usePublicClient } from "wagmi";
import { TxStatus } from "@/components/TxStatus";
import { Button, Card, Label, Notice, PageHeader, inputCls } from "@/components/ui";
import { api } from "@/lib/api";
import { DEPLOYMENT, TARGET_CHAIN, contracts } from "@/lib/chain";
import { useProfile } from "@/lib/local";
import { useTx } from "@/lib/tx";

type Unit = "minutes" | "days";
interface MilestoneDraft { title: string; detail: string; amount: string; dueIn: number; unit: Unit }

const secs = (n: number, u: Unit) => n * (u === "minutes" ? 60 : 86400);

export default function NewRaise() {
  const router = useRouter();
  const [profile] = useProfile();
  const { address } = useAccount();
  const { openConnectModal } = useConnectModal();
  const client = usePublicClient({ chainId: TARGET_CHAIN.id });
  const tx = useTx();
  const c = contracts();

  const [nickname, setNickname] = useState("");
  const [raiseIn, setRaiseIn] = useState(14);
  const [raiseUnit, setRaiseUnit] = useState<Unit>("days");
  const [ms, setMs] = useState<MilestoneDraft[]>([
    { title: "Pilot-scale batch meets lab spec", detail: "Independent measurement of the agreed spec on a pilot batch.", amount: "3000", dueIn: 30, unit: "days" },
    { title: "Third-party test report", detail: "Accredited lab report on the pilot output.", amount: "5000", dueIn: 90, unit: "days" },
  ]);
  const [steps, setSteps] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => { if (profile?.nickname) setNickname(profile.nickname); }, [profile]);

  const raiseSecs = secs(raiseIn, raiseUnit);
  const due = ms.map((m) => secs(m.dueIn, m.unit));
  const orderOk = due.every((d, i) => d > (i === 0 ? raiseSecs : due[i - 1]));
  const total = ms.reduce((a, m) => a + (Number(m.amount) || 0), 0);
  const valid = !!profile && nickname.trim() && ms.length > 0 && ms.every((m) => m.title && Number(m.amount) > 0) && orderOk;

  const update = (i: number, patch: Partial<MilestoneDraft>) => setMs(ms.map((m, j) => (j === i ? { ...m, ...patch } : m)));
  const log = (s: string) => setSteps((x) => [...x, s]);

  async function run() {
    if (!address) return openConnectModal?.();
    if (!profile || !c || !client) return;
    setRunning(true); setErr(null); setSteps([]);
    try {
      const meta: ProjectMetadata = {
        schema: "sci-protocol/project-metadata@1", nickname: nickname.trim(), fields: profile.fields, subdomains: profile.subdomains,
        trl: profile.trl, evidence: profile.evidence, country: profile.country, applicant_type: profile.applicant_type,
        uses_of_funds: profile.uses_of_funds, disclosure: "Non-confidential profile only. No method, composition or data is published.",
      };
      const pinned = await api.pinJson(meta);
      log(`Metadata pinned to IPFS (${pinned.pinned}): ${pinned.cid}`);

      const receipt = await tx.send("Register project", { ...c.registry, functionName: "registerProject", args: [pinned.cid, profile.trl] });
      const ev = receipt.logs
        .map((l) => { try { return decodeEventLog({ abi: c.registry.abi, data: l.data, topics: l.topics }); } catch { return null; } })
        .find((e) => e?.eventName === "ProjectRegistered");
      const pid = (ev?.args as any)?.projectId as bigint;
      log(`Project #${pid} registered`);

      const cids = await Promise.all(ms.map((m, i) => api.pinJson({ schema: "sci-protocol/milestone@1", index: i, title: m.title, detail: m.detail }).then((r) => r.cid)));
      log("Milestone descriptions pinned");

      // Deadlines are relative to chain time, so they're right on a local chain with shifted time too.
      const now = Number((await client.getBlock()).timestamp);
      const deadlines = due.map((d) => BigInt(now + d + 60));
      await tx.send("Set milestones", {
        ...c.escrow, functionName: "setMilestones",
        args: [pid, cids, ms.map((m) => parseUnits(m.amount, 6)), deadlines],
      });
      log("Milestones set in escrow");

      await tx.send("Open raise", { ...c.pool, functionName: "openCampaign", args: [pid, BigInt(now + raiseSecs + 30)] });
      log("Raise opened");
      router.push(`/raise/${pid}`);
    } catch (e) {
      setErr((e as Error).message?.split("\n")[0] ?? String(e));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader eyebrow={`On-chain · ${TARGET_CHAIN.name}`} title="Open a milestone-gated raise">
        Your non-confidential profile is pinned to IPFS and referenced on-chain. You define what the money is for, milestone by
        milestone. The raise is all-or-nothing; once funded, each milestone’s money is released only after an attestor approves your evidence.
      </PageHeader>
      {!DEPLOYMENT && <Notice tone="danger">Contracts aren’t deployed on {TARGET_CHAIN.name} yet (see docs/DEPLOY.md).</Notice>}
      {!profile && <Notice tone="danger">Build your <a className="underline" href="/profile">profile</a> first - its categories become the public project metadata.</Notice>}

      <Card className="space-y-5">
        <div>
          <Label hint="Public. Don't reveal anything confidential.">Project name</Label>
          <input className={inputCls} value={nickname} onChange={(e) => setNickname(e.target.value)} maxLength={80} />
        </div>

        <div>
          <Label hint="Milestones are paid in order. Use minutes for a live demo of the failure path.">Milestones</Label>
          <div className="space-y-3">
            {ms.map((m, i) => (
              <div key={i} className="grid gap-2 rounded-lg border border-neutral p-3 sm:grid-cols-[1fr_8rem_9rem_auto]">
                <div className="space-y-2">
                  <input className={inputCls} placeholder="Milestone (verifiable outcome)" value={m.title} onChange={(e) => update(i, { title: e.target.value })} />
                  <input className={inputCls} placeholder="How it will be verified" value={m.detail} onChange={(e) => update(i, { detail: e.target.value })} />
                </div>
                <div>
                  <span className="text-xs text-charcoal-muted">mUSDC</span>
                  <input className={inputCls} type="number" min={1} value={m.amount} onChange={(e) => update(i, { amount: e.target.value })} />
                </div>
                <div>
                  <span className="text-xs text-charcoal-muted">due in</span>
                  <div className="flex gap-1">
                    <input className={inputCls} type="number" min={1} value={m.dueIn} onChange={(e) => update(i, { dueIn: Number(e.target.value) })} />
                    <select className={inputCls} value={m.unit} onChange={(e) => update(i, { unit: e.target.value as Unit })}>
                      <option value="days">days</option><option value="minutes">min</option>
                    </select>
                  </div>
                </div>
                <button className="self-start text-sm text-charcoal-muted hover:text-error" onClick={() => setMs(ms.filter((_, j) => j !== i))} disabled={ms.length === 1}>✕</button>
              </div>
            ))}
          </div>
          <div className="mt-2 flex items-center justify-between">
            <Button variant="ghost" onClick={() => setMs([...ms, { title: "", detail: "", amount: "1000", dueIn: (ms.at(-1)?.dueIn ?? 30) + 30, unit: ms.at(-1)?.unit ?? "days" }])} disabled={ms.length >= 10}>+ Add milestone</Button>
            <span className="text-sm text-charcoal-soft">Total raise: <strong>{total.toLocaleString()} mUSDC</strong></span>
          </div>
        </div>

        <div className="max-w-sm">
          <Label hint="Must close before the first milestone is due.">Raise closes in</Label>
          <div className="flex gap-1">
            <input className={inputCls} type="number" min={1} value={raiseIn} onChange={(e) => setRaiseIn(Number(e.target.value))} />
            <select className={inputCls} value={raiseUnit} onChange={(e) => setRaiseUnit(e.target.value as Unit)}>
              <option value="days">days</option><option value="minutes">minutes</option>
            </select>
          </div>
        </div>
        {!orderOk && <Notice>Deadlines must increase: raise close &lt; milestone 1 &lt; milestone 2 …</Notice>}

        <div className="flex items-center gap-3 border-t border-neutral/70 pt-4">
          <Button disabled={!valid || running || !DEPLOYMENT} onClick={run}>{address ? "Create on-chain (3 transactions)" : "Connect wallet"}</Button>
          <span className="text-xs text-charcoal-muted">register → set milestones → open raise</span>
        </div>
        {steps.length > 0 && <ul className="space-y-1 text-sm text-lime-800">{steps.map((s) => <li key={s}>✓ {s}</li>)}</ul>}
        <TxStatus state={tx.state} />
        {err && tx.state.status !== "error" && <Notice tone="danger">{err}</Notice>}
      </Card>
    </div>
  );
}
