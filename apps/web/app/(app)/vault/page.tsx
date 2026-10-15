"use client";

import { useConnectModal } from "@rainbow-me/rainbowkit";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { decodeEventLog, type TransactionReceipt } from "viem";
import { useAccount, usePublicClient, useSignMessage } from "wagmi";
import { TxStatus } from "@/components/TxStatus";
import { Button, Card, Label, Notice, PageHeader, Spinner, cx, inputCls } from "@/components/ui";
import { api } from "@/lib/api";
import { DEPLOYMENT, TARGET_CHAIN, contracts, txUrl } from "@/lib/chain";
import { short } from "@/lib/format";
import { VAULT_MESSAGE, deriveKey, fileToB64, hashBlob, open, seal, type VaultPayload } from "@/lib/vault";
import { useTx } from "@/lib/tx";

interface Proof { hash: `0x${string}`; cid: string; pinned: string; tx?: string; submitter?: string; timestamp?: number }

function ProofCard({ p }: { p: Proof }) {
  return (
    <Card tone="positive" className="space-y-2">
      <p className="font-semibold text-lime-800">Existence proof</p>
      <dl className="grid gap-1 text-sm sm:grid-cols-[9rem_1fr]">
        <dt className="text-charcoal-muted">keccak256</dt><dd className="break-all font-mono text-xs">{p.hash}</dd>
        <dt className="text-charcoal-muted">Ciphertext CID</dt><dd className="break-all font-mono text-xs"><a className="underline" href={api.ipfsUrl(p.cid)} target="_blank" rel="noreferrer">{p.cid}</a> <span className="text-charcoal-muted">({p.pinned})</span></dd>
        {p.submitter && <><dt className="text-charcoal-muted">Anchored by</dt><dd className="font-mono text-xs">{p.submitter}</dd></>}
        {p.timestamp !== undefined && <><dt className="text-charcoal-muted">Timestamp</dt><dd>{new Date(p.timestamp * 1000).toUTCString()} (block time)</dd></>}
        {p.tx && <><dt className="text-charcoal-muted">Transaction</dt><dd className="font-mono text-xs">{txUrl(p.tx) ? <a className="underline" href={txUrl(p.tx)} target="_blank" rel="noreferrer">{short(p.tx, 8)}</a> : short(p.tx, 8)}</dd></>}
      </dl>
      <p className="text-xs text-lime-800">
        Proves this exact ciphertext existed and was anchored by this wallet at this time. It is <strong>not</strong> prior art,
        <strong> not</strong> a patent filing and <strong>not</strong> legal IP registration.
      </p>
    </Card>
  );
}

function VaultInner() {
  const search = useSearchParams();
  const { address } = useAccount();
  const { openConnectModal } = useConnectModal();
  const { signMessageAsync } = useSignMessage();
  const client = usePublicClient({ chainId: TARGET_CHAIN.id });
  const tx = useTx();
  const c = contracts();
  const [tab, setTab] = useState<"seal" | "verify">(search.get("hash") ? "verify" : "seal");

  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [projectId, setProjectId] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [proof, setProof] = useState<Proof | null>(null);

  const [lookup, setLookup] = useState(search.get("hash") ?? "");
  const [found, setFound] = useState<Proof | null>(null);
  const [blob, setBlob] = useState<Uint8Array | null>(null);
  const [opened, setOpened] = useState<VaultPayload | null>(null);

  async function key() {
    setBusy("Sign the message in your wallet to derive your key…");
    return deriveKey(await signMessageAsync({ message: VAULT_MESSAGE }));
  }

  async function doSeal() {
    if (!address) return openConnectModal?.();
    if (!c) return;
    setErr(null); setProof(null);
    try {
      const k = await key();
      setBusy("Encrypting in your browser…");
      const payload: VaultPayload = { text, sealedAt: new Date().toISOString() };
      if (file) payload.file = { name: file.name, type: file.type, b64: await fileToB64(file) };
      const { blob, hash } = await seal(k, payload);
      setBusy("Pinning ciphertext to IPFS…");
      const pinned = await api.pinBytes(blob);
      setBusy(null);
      const receipt: TransactionReceipt = await tx.send("Anchor hash", { ...c.attestations, functionName: "anchor", args: [hash, pinned.cid] });
      const ev = receipt.logs.map((l) => { try { return decodeEventLog({ abi: c.attestations.abi, data: l.data, topics: l.topics }); } catch { return null; } })
        .find((e) => e?.eventName === "Anchored");
      const args = ev?.args as { submitter: string; timestamp: bigint } | undefined;
      setProof({ hash, cid: pinned.cid, pinned: pinned.pinned, tx: receipt.transactionHash, submitter: args?.submitter, timestamp: Number(args?.timestamp ?? 0) });
      if (projectId) await tx.send("Link to project", { ...c.registry, functionName: "setPrivateDetailHash", args: [BigInt(projectId), hash] });
      setText(""); setFile(null);
    } catch (e) {
      if (tx.state.status !== "error") setErr((e as Error).message?.split("\n")[0] ?? String(e));
    } finally {
      setBusy(null);
    }
  }

  async function doLookup(q = lookup) {
    if (!c || !client || !q) return;
    setErr(null); setFound(null); setBlob(null); setOpened(null);
    try {
      let hash = q.trim() as `0x${string}`;
      let bytes: Uint8Array | null = null;
      if (!/^0x[0-9a-fA-F]{64}$/.test(hash)) {
        setBusy("Fetching ciphertext from IPFS…");
        const r = await fetch(api.ipfsUrl(q.trim()));
        if (!r.ok) throw new Error("CID not found");
        bytes = new Uint8Array(await r.arrayBuffer());
        hash = hashBlob(bytes);
      }
      const a = (await client.readContract({ ...c.attestations, functionName: "getAnchor", args: [hash] })) as { submitter: string; timestamp: bigint; cid: string };
      if (/^0x0+$/.test(a.submitter)) throw new Error("No anchor for this hash on " + TARGET_CHAIN.name);
      if (!bytes && a.cid) {
        const r = await fetch(api.ipfsUrl(a.cid));
        if (r.ok) bytes = new Uint8Array(await r.arrayBuffer());
      }
      if (bytes && hashBlob(bytes) !== hash) throw new Error("Ciphertext does not match the anchored hash");
      setBlob(bytes);
      setFound({ hash, cid: a.cid, pinned: "ipfs", submitter: a.submitter, timestamp: Number(a.timestamp) });
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function doOpen() {
    if (!blob) return;
    if (!address) return openConnectModal?.();
    try {
      const k = await key();
      setOpened(await open(k, blob));
    } catch {
      setErr("Couldn't decrypt - only the wallet that sealed it can open it.");
    } finally {
      setBusy(null);
    }
  }

  useEffect(() => { if (search.get("hash") && c && client) doLookup(search.get("hash")!); }, [c, client]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader eyebrow="Private vault" title="Timestamp confidential details - without disclosing them">
        Encrypted in your browser with a key derived from your wallet signature. Only the ciphertext is pinned to IPFS; only its
        keccak256 hash and CID go on-chain. Nobody - including us - can read it.
      </PageHeader>
      {!DEPLOYMENT && <Notice tone="danger">Contracts aren’t deployed on {TARGET_CHAIN.name} yet.</Notice>}

      <div className="flex gap-2">
        {(["seal", "verify"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={cx("rounded-full px-4 py-1.5 text-sm font-semibold", tab === t ? "bg-lime text-charcoal" : "bg-white text-charcoal-soft ring-1 ring-inset ring-neutral hover:text-charcoal")}>
            {t === "seal" ? "Seal & anchor" : "Verify / open"}
          </button>
        ))}
      </div>

      {tab === "seal" && (
        <Card className="space-y-4">
          <div>
            <Label hint="Method, composition, data - whatever you'd never upload in plain text. It is encrypted before it leaves this page.">Confidential details</Label>
            <textarea className={inputCls} rows={6} value={text} onChange={(e) => setText(e.target.value)} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label hint="Optional, encrypted with the text (5 MB max).">Attach a file</Label>
              <input type="file" className="text-sm" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </div>
            <div>
              <Label hint="Optional: link the proof to a project you registered.">Project id</Label>
              <input className={inputCls} value={projectId} onChange={(e) => setProjectId(e.target.value.replace(/\D/g, ""))} placeholder="e.g. 1" />
            </div>
          </div>
          <Button disabled={(!text && !file) || !!busy || tx.busy || !DEPLOYMENT} onClick={doSeal}>{address ? "Encrypt, pin & anchor" : "Connect wallet"}</Button>
          {busy && <p className="flex items-center gap-2 text-sm text-charcoal-muted"><Spinner /> {busy}</p>}
          <TxStatus state={tx.state} />
          {err && <Notice tone="danger">{err}</Notice>}
        </Card>
      )}
      {tab === "seal" && proof && <ProofCard p={proof} />}

      {tab === "verify" && (
        <Card className="space-y-4">
          <div>
            <Label hint="Anyone can verify an anchor. Only the sealing wallet can decrypt.">Hash (0x…) or ciphertext CID</Label>
            <div className="flex gap-2">
              <input className={inputCls} value={lookup} onChange={(e) => setLookup(e.target.value)} />
              <Button onClick={() => doLookup()} disabled={!lookup || !!busy}>Verify</Button>
            </div>
          </div>
          {busy && <p className="flex items-center gap-2 text-sm text-charcoal-muted"><Spinner /> {busy}</p>}
          {err && <Notice tone="danger">{err}</Notice>}
          {found && <ProofCard p={found} />}
          {found && blob && !opened && <Button variant="secondary" onClick={doOpen}>Decrypt with my wallet</Button>}
          {opened && (
            <Card className="space-y-2">
              <p className="text-xs text-charcoal-muted">Decrypted locally · sealed {opened.sealedAt}</p>
              <p className="whitespace-pre-wrap text-sm">{opened.text}</p>
              {opened.file && <a className="text-sm underline" download={opened.file.name} href={`data:${opened.file.type || "application/octet-stream"};base64,${opened.file.b64}`}>{opened.file.name}</a>}
            </Card>
          )}
        </Card>
      )}
      <p className="text-xs text-charcoal-muted">Uses a deterministic wallet signature as key material - works with standard EOAs (MetaMask, Rabby). Smart-contract wallets may not reproduce the same signature.</p>
    </div>
  );
}

export default function VaultPage() {
  return <Suspense><VaultInner /></Suspense>;
}
