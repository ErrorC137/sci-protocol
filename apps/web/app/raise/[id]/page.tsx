"use client";

import { useConnectModal } from "@rainbow-me/rainbowkit";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { parseUnits } from "viem";
import { useAccount } from "wagmi";
import { TxStatus } from "@/components/TxStatus";
import { Button, Card, Chip, Empty, Notice, PageHeader, Spinner, cx, inputCls } from "@/components/ui";
import { api } from "@/lib/api";
import { DEPLOYMENT, MILESTONE_STATE, PROJECT_STATUS, addressUrl, contracts } from "@/lib/chain";
import { countdown, looksLikeCid, short, usdc } from "@/lib/format";
import { isZeroHash, useMetadata, useProject, type Milestone, type ProjectState } from "@/lib/hooks";
import { useTx } from "@/lib/tx";

const STATUS_TONE = ["slate", "blue", "violet", "green", "red"] as const;
const MS_TONE = ["slate", "blue", "green", "red", "violet"] as const;

function MilestoneText({ cid }: { cid: string }) {
  const q = useQuery({
    queryKey: ["ms", cid], enabled: looksLikeCid(cid), staleTime: Infinity,
    queryFn: () => api.ipfsJson<{ title: string; detail?: string }>(cid),
  });
  if (!looksLikeCid(cid)) return <p className="font-medium text-ink">{cid}</p>;
  return (
    <div>
      <p className="font-medium text-ink">{q.data?.title ?? "…"}</p>
      {q.data?.detail && <p className="text-xs text-ink-muted">{q.data.detail}</p>}
    </div>
  );
}

function Section({ title, children, aside }: { title: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <Card>
      <div className="mb-3 flex items-center justify-between gap-2"><h2 className="font-semibold text-ink">{title}</h2>{aside}</div>
      {children}
    </Card>
  );
}

export default function Campaign({ params }: { params: { id: string } }) {
  const pid = /^\d+$/.test(params.id) ? BigInt(params.id) : undefined;
  const { address } = useAccount();
  const { openConnectModal } = useConnectModal();
  const q = useProject(pid);
  const meta = useMetadata(q.data?.metadataCID);
  const activity = useQuery({ queryKey: ["activity", params.id], queryFn: () => api.activity(Number(params.id)), refetchInterval: 6000, retry: false });
  const tx = useTx();
  const c = contracts();
  const [amount, setAmount] = useState("1000");
  const [evidence, setEvidence] = useState("");
  const [reason, setReason] = useState("");
  const [revenue, setRevenue] = useState("500");

  if (!DEPLOYMENT || !c) return <Notice tone="red">Contracts aren’t deployed on this chain (docs/DEPLOY.md).</Notice>;
  if (pid === undefined) return <Empty title="Invalid project id" />;
  if (q.isLoading) return <Card className="flex items-center gap-2"><Spinner /> Reading project #{params.id} from chain…</Card>;
  if (q.error || !q.data) return <Empty title={`Project #${params.id} not found on this chain`} />;

  const s: ProjectState = q.data;
  const me = s.me;
  const now = s.chainNow;
  const run = (label: string, call: Parameters<typeof tx.send>[1]) => tx.send(label, call).then(() => q.refetch()).catch(() => {});
  // tx.send already reports failures in <TxStatus>; this just stops a failed step from becoming an unhandled rejection.
  const safe = (fn: () => Promise<unknown>) => () => { fn().catch(() => {}); };
  const needWallet = !address;
  const fullyFunded = s.ledger.budget > 0n && s.ledger.deposited === s.ledger.budget;
  const raiseOpen = s.campaign.exists && !s.campaign.finalized && now <= Number(s.campaign.deadline);
  const remaining = s.campaign.target - s.campaign.raised;

  async function contribute() {
    const amt = parseUnits(amount || "0", 6);
    if (me && me.allowancePool < amt) await tx.send("Approve mUSDC", { ...c!.usdc, functionName: "approve", args: [c!.pool.address, amt] });
    await run("Contribute", { ...c!.pool, functionName: "contribute", args: [pid, amt] });
  }

  async function submitEvidence(i: number) {
    const pinned = await api.pinJson({ schema: "sci-protocol/evidence@1", projectId: params.id, milestone: i, summary: evidence });
    await run(`Submit evidence for milestone ${i + 1}`, { ...c!.escrow, functionName: "submitEvidence", args: [pid, BigInt(i), pinned.cid] });
    setEvidence("");
  }

  async function reject(i: number) {
    const pinned = await api.pinJson({ schema: "sci-protocol/rejection@1", projectId: params.id, milestone: i, reason });
    await run(`Reject milestone ${i + 1}`, { ...c!.escrow, functionName: "rejectMilestone", args: [pid, BigInt(i), pinned.cid] });
    setReason("");
  }

  async function distribute() {
    const amt = parseUnits(revenue || "0", 6);
    await tx.send("Approve mUSDC", { ...c!.usdc, functionName: "approve", args: [c!.fractions.address, amt] });
    await run("Distribute revenue", { ...c!.fractions, functionName: "distributeRevenue", args: [pid, amt] });
  }

  const role = me?.isResearcher ? "Researcher" : me?.isAttestor ? "Attestor" : me && me.contribution > 0n ? "Funder" : me ? "Visitor" : null;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow={`Project #${params.id}`} title={meta.data?.nickname ?? `Project #${params.id}`}>
        <span className="flex flex-wrap items-center gap-2">
          <Chip tone={STATUS_TONE[s.status]}>{PROJECT_STATUS[s.status]}</Chip>
          <Chip>TRL {s.trl}</Chip>
          {meta.data?.subdomains?.map((x) => <Chip key={x}>{x}</Chip>)}
          <span className="text-xs text-ink-muted">researcher <a className="underline" href={addressUrl(s.researcher)} target="_blank" rel="noreferrer">{short(s.researcher)}</a></span>
          <a className="text-xs text-ink-muted underline" href={api.ipfsUrl(s.metadataCID)} target="_blank" rel="noreferrer">metadata</a>
          {!isZeroHash(s.privateDetailHash) && <Link className="text-xs text-emerald-700 underline" href={`/vault?hash=${s.privateDetailHash}`}>🔒 vault proof linked</Link>}
        </span>
      </PageHeader>

      <Card className="flex flex-wrap items-center gap-3 text-sm">
        {needWallet ? (
          <><span className="text-ink-soft">Connect a wallet to fund, submit evidence or attest.</span><Button onClick={() => openConnectModal?.()}>Connect wallet</Button></>
        ) : (
          <>
            <span>You are: <strong>{role}</strong></span>
            <span className="text-ink-muted">· {usdc(me?.usdc)} mUSDC</span>
            <Button variant="secondary" disabled={tx.busy} onClick={() => run("Get test mUSDC", { ...c.usdc, functionName: "faucet", args: [] })}>Get 10,000 test mUSDC</Button>
          </>
        )}
        <div className="w-full"><TxStatus state={tx.state} /></div>
      </Card>

      {s.refundable && (
        <Card className="border-rose-300 bg-rose-50">
          <p className="text-lg font-semibold text-rose-900">Milestone {s.current + 1} missed its deadline.</p>
          <p className="mt-1 text-sm text-rose-900">No accepted evidence arrived in time. Anyone can trigger the refund: the {usdc(s.ledger.deposited - s.ledger.released, 0)} mUSDC never released goes back to funders, pro-rata.</p>
          <div className="mt-3"><Button variant="danger" disabled={needWallet || tx.busy} onClick={() => run("Trigger refund", { ...c.escrow, functionName: "refundRemaining", args: [pid] })}>Trigger refund</Button></div>
        </Card>
      )}
      {s.ledger.failed && (
        <Card className="border-rose-300 bg-rose-50">
          <p className="text-lg font-semibold text-rose-900">Project failed - funds are being returned.</p>
          <p className="mt-1 text-sm text-rose-900">Refund pot {usdc(s.ledger.refundPot)} mUSDC · already refunded {usdc(s.ledger.refunded)} mUSDC · the researcher kept only the {usdc(s.ledger.released)} mUSDC earned by approved milestones.</p>
          {me && me.refundableAmount > 0n && (
            <div className="mt-3"><Button variant="danger" disabled={tx.busy} onClick={() => run("Claim refund", { ...c.escrow, functionName: "claimRefund", args: [pid] })}>Claim my refund: {usdc(me.refundableAmount)} mUSDC</Button></div>
          )}
          {me?.refundClaimed && <p className="mt-2 text-sm font-semibold text-emerald-800">✓ Your refund has been paid.</p>}
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
        <div className="space-y-6">
          <Section title="Milestones" aside={<span className="text-xs text-ink-muted">paid in order, after attestor approval</span>}>
            <ol className="space-y-3">
              {s.milestones.map((m: Milestone, i) => {
                const secsLeft = Number(m.deadline) - now;
                const isCurrent = i === s.current && !s.ledger.failed;
                return (
                  <li key={i} className={cx("rounded-lg border p-3", isCurrent ? "border-brand-500 bg-brand-50/40" : "border-slate-200")}>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="flex gap-3">
                        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-white text-sm font-bold text-brand-700 ring-1 ring-brand-100">{i + 1}</span>
                        <MilestoneText cid={m.descriptionCID} />
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold tabular-nums">{usdc(m.amount, 0)} mUSDC</span>
                        {s.ledger.failed && i === s.current
                          ? <Chip tone="red">Missed</Chip>
                          : <Chip tone={MS_TONE[m.state]}>{MILESTONE_STATE[m.state]}</Chip>}
                      </div>
                    </div>
                    <p className={cx("mt-1 text-xs", secsLeft < 0 && m.state < 2 ? "font-semibold text-rose-700" : "text-ink-muted")}>
                      Due {new Date(Number(m.deadline) * 1000).toLocaleString()} · {secsLeft > 0 ? `${countdown(secsLeft)} left` : "deadline passed"}
                    </p>
                    {m.evidenceCID && <a className="mt-1 inline-block text-xs text-brand-700 underline" href={api.ipfsUrl(m.evidenceCID)} target="_blank" rel="noreferrer">evidence on IPFS</a>}

                    {isCurrent && me?.isResearcher && (m.state === 0 || m.state === 3) && secsLeft > 0 && (
                      <div className="mt-3 space-y-2">
                        {!fullyFunded && <p className="text-xs text-ink-muted">Evidence can be submitted once the escrow is fully funded.</p>}
                        <textarea className={inputCls} rows={2} placeholder="Evidence summary (non-confidential) - e.g. link to test report" value={evidence} onChange={(e) => setEvidence(e.target.value)} />
                        <Button disabled={!evidence || !fullyFunded || tx.busy} onClick={safe(() => submitEvidence(i))}>Submit evidence</Button>
                      </div>
                    )}
                    {m.state === 1 && me?.isAttestor && (
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <Button disabled={tx.busy} onClick={() => run(`Approve milestone ${i + 1}`, { ...c.escrow, functionName: "approveMilestone", args: [pid, BigInt(i)] })}>Approve</Button>
                        <input className={cx(inputCls, "max-w-xs")} placeholder="Reason (if rejecting)" value={reason} onChange={(e) => setReason(e.target.value)} />
                        <Button variant="secondary" disabled={!reason || tx.busy} onClick={safe(() => reject(i))}>Reject</Button>
                      </div>
                    )}
                    {m.state === 1 && !me?.isAttestor && <p className="mt-2 text-xs text-ink-muted">Awaiting attestor review. Review latency never counts against the researcher.</p>}
                    {m.state === 2 && (
                      <div className="mt-3"><Button disabled={needWallet || tx.busy} onClick={() => run(`Release milestone ${i + 1}`, { ...c.escrow, functionName: "releaseMilestone", args: [pid, BigInt(i)] })}>Release {usdc(m.amount, 0)} mUSDC to researcher</Button></div>
                    )}
                  </li>
                );
              })}
            </ol>
          </Section>

          <Section title="Activity">
            {activity.error ? <p className="text-sm text-ink-muted">The event feed needs the API indexer (INDEXER_ENABLED=true). Contract state above is read live from chain.</p> : (
              <ul className="space-y-1 text-sm">
                {activity.data?.events.map((e) => (
                  <li key={`${e.tx}-${e.log_index}`} className="flex justify-between gap-2">
                    <span><span className="font-medium text-ink">{e.event}</span> <span className="text-ink-muted">{e.contract}</span></span>
                    <span className="text-xs text-ink-muted">block {e.block}</span>
                  </li>
                ))}
                {activity.data?.events.length === 0 && <li className="text-ink-muted">No events yet.</li>}
              </ul>
            )}
          </Section>
        </div>

        <div className="space-y-6">
          <Section title="Raise">
            {s.campaign.exists ? (
              <>
                <p className="text-2xl font-bold text-ink">{usdc(s.campaign.raised, 0)} <span className="text-base font-normal text-ink-muted">/ {usdc(s.campaign.target, 0)} mUSDC</span></p>
                <div className="mt-2 h-2 rounded-full bg-slate-100">
                  <div className="h-2 rounded-full bg-brand-500" style={{ width: `${s.campaign.target ? Number((s.campaign.raised * 100n) / s.campaign.target) : 0}%` }} />
                </div>
                <p className="mt-2 text-xs text-ink-muted">
                  {s.campaign.finalized ? "Fully funded - money is in milestone escrow." : raiseOpen ? `Closes in ${countdown(Number(s.campaign.deadline) - now)} · all-or-nothing` : "Raise closed without reaching its target."}
                </p>
                {raiseOpen && (
                  <div className="mt-3 flex gap-2">
                    <input className={inputCls} type="number" min={1} value={amount} onChange={(e) => setAmount(e.target.value)} />
                    <Button disabled={tx.busy || !Number(amount)} onClick={needWallet ? () => openConnectModal?.() : safe(contribute)}>Contribute</Button>
                  </div>
                )}
                {raiseOpen && <button className="mt-1 text-xs text-brand-700 underline" onClick={() => setAmount(String(Number(remaining) / 1e6))}>fill remaining ({usdc(remaining, 0)})</button>}
                {me && me.contribution > 0n && <p className="mt-3 text-sm">Your contribution: <strong>{usdc(me.contribution)} mUSDC</strong></p>}
                {s.raiseFailed && me && me.contribution > 0n && !me.withdrawn && (
                  <div className="mt-3"><Button variant="danger" disabled={tx.busy} onClick={() => run("Withdraw", { ...c.pool, functionName: "withdrawIfFailed", args: [pid] })}>Withdraw my contribution</Button></div>
                )}
              </>
            ) : <p className="text-sm text-ink-muted">No crowd raise (sponsor-funded or not yet opened).</p>}
          </Section>

          <Section title="Escrow ledger">
            <dl className="grid grid-cols-2 gap-y-1 text-sm">
              <dt className="text-ink-muted">Budget</dt><dd className="text-right tabular-nums">{usdc(s.ledger.budget, 0)}</dd>
              <dt className="text-ink-muted">Deposited</dt><dd className="text-right tabular-nums">{usdc(s.ledger.deposited, 0)}</dd>
              <dt className="text-ink-muted">Released</dt><dd className="text-right tabular-nums">{usdc(s.ledger.released, 0)}</dd>
              <dt className="text-ink-muted">Held</dt><dd className="text-right font-semibold tabular-nums">{usdc(s.ledger.deposited - s.ledger.released - s.ledger.refunded, 0)}</dd>
              {s.ledger.failed && <><dt className="text-ink-muted">Refunded</dt><dd className="text-right tabular-nums">{usdc(s.ledger.refunded, 0)}</dd></>}
            </dl>
          </Section>

          {s.campaign.finalized && !s.ledger.failed && (
            <Section title="Fractions & revenue" aside={<Chip tone="amber">mechanism demo</Chip>}>
              <p className="text-xs text-ink-muted">ERC-1155 id #{params.id}: one unit per mUSDC base unit contributed. A pro-rata claim on revenue routed here. Testnet only - not a securities offering.</p>
              {me && me.contribution > 0n && !me.fractionsClaimed && (
                <div className="mt-3"><Button variant="secondary" disabled={tx.busy} onClick={() => run("Claim fractions", { ...c.pool, functionName: "claimFractions", args: [pid] })}>Claim my fractions</Button></div>
              )}
              {me && me.fractions > 0n && <p className="mt-3 text-sm">You hold <strong>{usdc(me.fractions)}</strong> fractions · claimable revenue <strong>{usdc(me.revenue)}</strong> mUSDC</p>}
              {me && me.revenue > 0n && <div className="mt-2"><Button variant="secondary" disabled={tx.busy} onClick={() => run("Claim revenue", { ...c.fractions, functionName: "claimRevenue", args: [pid] })}>Claim revenue</Button></div>}
              <div className="mt-3 flex gap-2">
                <input className={inputCls} type="number" min={1} value={revenue} onChange={(e) => setRevenue(e.target.value)} />
                <Button variant="secondary" disabled={needWallet || tx.busy} onClick={safe(distribute)}>Route revenue</Button>
              </div>
            </Section>
          )}
        </div>
      </div>
    </div>
  );
}
