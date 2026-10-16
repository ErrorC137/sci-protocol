"use client";

import {
  AttestationRegistryAbi, FundingPoolAbi, MilestoneEscrowAbi, MockUSDCAbi, ProjectRegistryAbi, SCIFractionAbi, type Deployment,
} from "@sci/shared";
import { useEffect, useState } from "react";
import { getAddress, isAddress, type Abi, type Hex } from "viem";
import { useAccount, usePublicClient, useSwitchChain } from "wagmi";
import { getWalletClient } from "wagmi/actions";
import { WalletButton } from "@/components/WalletButton";
import { Button, Card, Chip, Label, Notice, PageHeader, cx, inputCls } from "@/components/ui";
import { API_URL } from "@/lib/api";
import { DEPLOYMENT, TARGET_CHAIN, addressUrl, txUrl, wagmiConfig } from "@/lib/chain";
import { errorMessage } from "@/lib/tx";

// Deploys the protocol from the connected wallet - the same contracts and role wiring as
// contracts/script/Wiring.sol - so no private key has to sit in a server or CI. 13 wallet confirmations.

type Name = "MockUSDC" | "ProjectRegistry" | "AttestationRegistry" | "SCIFraction" | "MilestoneEscrow" | "FundingPool";
type Addrs = Partial<Record<Name, `0x${string}`>>;
interface Progress { addrs: Addrs; done: string[]; startBlock?: number; hashes: Record<string, Hex>; attestor?: `0x${string}` }

const ABI: Record<Name, Abi> = {
  MockUSDC: MockUSDCAbi as Abi, ProjectRegistry: ProjectRegistryAbi as Abi, AttestationRegistry: AttestationRegistryAbi as Abi,
  SCIFraction: SCIFractionAbi as Abi, MilestoneEscrow: MilestoneEscrowAbi as Abi, FundingPool: FundingPoolAbi as Abi,
};

interface Step {
  id: string;
  label: string;
  deploy?: Name;
  args?: (a: Required<Addrs>, admin: `0x${string}`, uri: string) => unknown[];
  call?: (a: Required<Addrs>, attestor: `0x${string}`) => { target: Name; fn: string; role?: [Name, string]; args: (role?: Hex) => unknown[] };
}

const STEPS: Step[] = [
  { id: "usdc", label: "Deploy MockUSDC (test stablecoin with a faucet)", deploy: "MockUSDC", args: () => [] },
  { id: "registry", label: "Deploy ProjectRegistry", deploy: "ProjectRegistry", args: (_a, admin) => [admin] },
  { id: "attest", label: "Deploy AttestationRegistry", deploy: "AttestationRegistry", args: (_a, admin) => [admin] },
  { id: "fractions", label: "Deploy SCIFraction (ERC-1155 backer receipts)", deploy: "SCIFraction", args: (a, admin, uri) => [uri, a.MockUSDC, admin] },
  { id: "escrow", label: "Deploy MilestoneEscrow", deploy: "MilestoneEscrow", args: (a, admin) => [a.MockUSDC, a.ProjectRegistry, admin] },
  { id: "pool", label: "Deploy FundingPool", deploy: "FundingPool", args: (a) => [a.MockUSDC, a.ProjectRegistry, a.MilestoneEscrow, a.SCIFraction] },
  { id: "w1", label: "Escrow: set the pool", call: (a) => ({ target: "MilestoneEscrow", fn: "setPool", args: () => [a.FundingPool] }) },
  { id: "w2", label: "Registry: pool may update projects", call: (a) => ({ target: "ProjectRegistry", fn: "grantRole", role: ["ProjectRegistry", "MODULE_ROLE"], args: (r) => [r, a.FundingPool] }) },
  { id: "w3", label: "Registry: escrow may update projects", call: (a) => ({ target: "ProjectRegistry", fn: "grantRole", role: ["ProjectRegistry", "MODULE_ROLE"], args: (r) => [r, a.MilestoneEscrow] }) },
  { id: "w4", label: "Fractions: pool may mint receipts", call: (a) => ({ target: "SCIFraction", fn: "grantRole", role: ["SCIFraction", "MINTER_ROLE"], args: (r) => [r, a.FundingPool] }) },
  { id: "w5", label: "Registry: attestor role", call: (_a, at) => ({ target: "ProjectRegistry", fn: "grantRole", role: ["ProjectRegistry", "ATTESTOR_ROLE"], args: (r) => [r, at] }) },
  { id: "w6", label: "Escrow: attestor role", call: (_a, at) => ({ target: "MilestoneEscrow", fn: "grantRole", role: ["MilestoneEscrow", "ATTESTOR_ROLE"], args: (r) => [r, at] }) },
  { id: "w7", label: "AttestationRegistry: attestor role", call: (_a, at) => ({ target: "AttestationRegistry", fn: "grantRole", role: ["AttestationRegistry", "ATTESTOR_ROLE"], args: (r) => [r, at] }) },
];

const key = (chainId: number, who: string) => `uplo.setup.${chainId}.${who.toLowerCase()}`;
const load = (k: string): Progress => {
  try {
    const v = localStorage.getItem(k);
    if (v) return JSON.parse(v) as Progress;
  } catch { /* private mode / blocked storage: start fresh */ }
  return { addrs: {}, done: [], hashes: {} };
};
const save = (k: string, p: Progress) => { try { localStorage.setItem(k, JSON.stringify(p)); } catch { /* ignore */ } };

export default function Setup() {
  const { address, chainId } = useAccount();
  const client = usePublicClient({ chainId: TARGET_CHAIN.id });
  const { switchChainAsync } = useSwitchChain();
  const [attestor, setAttestor] = useState("");
  const [p, setP] = useState<Progress>({ addrs: {}, done: [], hashes: {} });
  const [running, setRunning] = useState(false);
  const [current, setCurrent] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [balance, setBalance] = useState<bigint | null>(null);
  const [copied, setCopied] = useState(false);
  const uri = `${API_URL.replace(/\/$/, "")}/chain/fractions/{id}.json`;

  useEffect(() => {
    if (address) setP(load(key(TARGET_CHAIN.id, address)));
  }, [address]);
  useEffect(() => {
    if (!address || !client) return;
    client.getBalance({ address }).then(setBalance).catch(() => setBalance(null));
  }, [address, client, p.done.length]);

  const attestorAddr = (attestor.trim() && isAddress(attestor.trim()) ? getAddress(attestor.trim()) : address) as `0x${string}` | undefined;
  const complete = STEPS.every((s) => p.done.includes(s.id));
  const mainnet = TARGET_CHAIN.testnet !== true && TARGET_CHAIN.id !== 31337;
  const deployment: Deployment | null = complete && address && attestorAddr ? {
    chainId: TARGET_CHAIN.id, startBlock: p.startBlock ?? 0, deployer: address, attestor: p.attestor ?? attestorAddr,
    MockUSDC: p.addrs.MockUSDC!, ProjectRegistry: p.addrs.ProjectRegistry!, AttestationRegistry: p.addrs.AttestationRegistry!,
    SCIFraction: p.addrs.SCIFraction!, MilestoneEscrow: p.addrs.MilestoneEscrow!, FundingPool: p.addrs.FundingPool!,
  } : null;
  const json = deployment ? JSON.stringify(deployment) : "";

  async function run() {
    if (!address || !client || !attestorAddr || mainnet) return;
    setErr(null);
    setRunning(true);
    const k = key(TARGET_CHAIN.id, address);
    let prog = load(k);
    try {
      if (chainId !== TARGET_CHAIN.id) await switchChainAsync({ chainId: TARGET_CHAIN.id });
      const wallet = await getWalletClient(wagmiConfig, { chainId: TARGET_CHAIN.id });
      // The attestor is fixed by the first step, so a reload can't silently grant the roles to someone else.
      if (!prog.attestor) { prog = { ...prog, attestor: attestorAddr }; save(k, prog); }
      const attestorFixed = prog.attestor!;
      const { default: bytecode } = await import("@/lib/bytecode.json");
      for (const s of STEPS) {
        if (prog.done.includes(s.id)) continue;
        setCurrent(s.id);
        let hash: Hex | undefined;
        let rc: Awaited<ReturnType<typeof client.waitForTransactionReceipt>> | undefined;
        const sent = prog.hashes[s.id];
        if (sent) {  // a tx sent before a reload / timeout may already be mined: never send it twice
          try {
            const old = await client.waitForTransactionReceipt({ hash: sent, timeout: 30_000 });
            if (old.status === "success" && old.transactionHash === sent) { hash = sent; rc = old; }
          } catch { /* dropped or still unknown: send again below */ }
        }
        if (!hash && s.deploy) {
          hash = await wallet.deployContract({
            abi: ABI[s.deploy], bytecode: (bytecode as Record<string, string>)[s.deploy] as Hex,
            args: s.args!(prog.addrs as Required<Addrs>, address, uri), account: address, chain: TARGET_CHAIN,
          });
        } else if (!hash) {
          const c = s.call!(prog.addrs as Required<Addrs>, attestorFixed);
          const role = c.role
            ? (await client.readContract({ address: prog.addrs[c.role[0]]!, abi: ABI[c.role[0]], functionName: c.role[1] })) as Hex
            : undefined;
          hash = await wallet.writeContract({
            address: prog.addrs[c.target]!, abi: ABI[c.target], functionName: c.fn, args: c.args(role), account: address, chain: TARGET_CHAIN,
          });
        }
        if (!hash) throw new Error(`${s.label}: nothing was sent`);
        if (!rc) {
          prog = { ...prog, hashes: { ...prog.hashes, [s.id]: hash } };
          save(k, prog);
          rc = await client.waitForTransactionReceipt({ hash, timeout: 180_000 });
        }
        if (rc.transactionHash !== hash) throw new Error(`${s.label}: the transaction was cancelled or replaced in the wallet. Press Continue to send it again.`);
        if (rc.status !== "success") throw new Error(`${s.label}: transaction reverted (${hash})`);
        if (s.deploy) {
          if (!rc.contractAddress) throw new Error(`${s.label}: no contract address in the receipt`);
          prog = { ...prog, addrs: { ...prog.addrs, [s.deploy]: getAddress(rc.contractAddress) } };
          if (prog.startBlock === undefined) prog.startBlock = Number(rc.blockNumber);
        }
        prog = { ...prog, done: [...prog.done, s.id] };
        save(k, prog);
        setP(prog);
      }
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setRunning(false);
      setCurrent(null);
    }
  }

  function reset() {
    if (!address) return;
    if (!confirm("Forget this browser's progress and start a fresh deployment? Contracts already on-chain stay there.")) return;
    const fresh = { addrs: {}, done: [], hashes: {} };
    save(key(TARGET_CHAIN.id, address), fresh);
    setP(fresh);
  }

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Setup" title={`Deploy the contracts to ${TARGET_CHAIN.name}`}>
        One-time setup for a new testnet. Your wallet deploys the six protocol contracts and wires their roles
        (the same steps as <code>contracts/script/Wiring.sol</code>): 13 confirmations, each needing a little test gas.
        No private key is stored anywhere but your wallet.
      </PageHeader>

      {DEPLOYMENT && (
        <Notice tone="positive">
          This build already has contracts on {TARGET_CHAIN.name} (registry{" "}
          <a className="underline" href={addressUrl(DEPLOYMENT.ProjectRegistry)} target="_blank" rel="noreferrer">{DEPLOYMENT.ProjectRegistry.slice(0, 10)}…</a>).
          Only deploy again if you mean to start a fresh set.
        </Notice>
      )}
      {TARGET_CHAIN.testnet !== true && TARGET_CHAIN.id !== 31337 && (
        <Notice tone="danger">{TARGET_CHAIN.name} is a mainnet. This page deploys a test stablecoin with an open faucet; do not use it here.</Notice>
      )}

      <Card className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <WalletButton />
          {address && balance !== null && (
            <span className="text-sm text-charcoal-soft">
              Gas balance: {(Number(balance) / 1e18).toFixed(4)} {TARGET_CHAIN.nativeCurrency.symbol}
              {balance === 0n && TARGET_CHAIN.id === 43113 && <> - get test AVAX from the <a className="underline" href="https://core.app/tools/testnet-faucet/?subnet=c&token=c" target="_blank" rel="noreferrer">Avalanche faucet</a></>}
            </span>
          )}
        </div>
        <Label hint="Wallet allowed to approve milestone evidence and anchor evidence hashes. Defaults to the deploying wallet.">
          Attestor address
        </Label>
        <input className={inputCls} placeholder={address ?? "0x…"} value={p.attestor ?? attestor} onChange={(e) => setAttestor(e.target.value)} disabled={running || p.done.length > 0} />
        {attestor.trim() && !isAddress(attestor.trim()) && <p className="text-xs text-error">Not a valid address.</p>}
        <p className="text-xs text-charcoal-muted">Fraction metadata URI: <code>{uri}</code></p>
        <div className="flex flex-wrap gap-3">
          <Button onClick={run} disabled={!address || running || complete || mainnet || (!!attestor.trim() && !isAddress(attestor.trim()))}>
            {running ? "Deploying… confirm each step in your wallet" : p.done.length ? "Continue deployment" : "Deploy contracts"}
          </Button>
          {p.done.length > 0 && !running && <Button variant="ghost" onClick={reset}>Start over</Button>}
        </div>
        {err && <Notice tone="danger">{err} {p.done.length > 0 && "Progress is saved: press Continue to pick up from this step."}</Notice>}
      </Card>

      <Card className="space-y-2">
        <h3 className="font-semibold text-charcoal">Steps</h3>
        <ol className="space-y-1 text-sm">
          {STEPS.map((s, i) => {
            const done = p.done.includes(s.id);
            const h = p.hashes[s.id];
            return (
              <li key={s.id} className={cx("flex flex-wrap items-center gap-2", !done && current !== s.id && "text-charcoal-muted")}>
                <span className="w-6 font-mono text-xs">{i + 1}.</span>
                {s.label}
                {done ? <Chip tone="positive">done</Chip> : current === s.id ? <Chip tone="caution">waiting for wallet / block</Chip> : null}
                {s.deploy && p.addrs[s.deploy] && <a className="font-mono text-xs underline" href={addressUrl(p.addrs[s.deploy]!)} target="_blank" rel="noreferrer">{p.addrs[s.deploy]}</a>}
                {h && txUrl(h) && <a className="text-xs underline" href={txUrl(h)} target="_blank" rel="noreferrer">tx</a>}
              </li>
            );
          })}
        </ol>
      </Card>

      {deployment && (
        <Card className="space-y-3">
          <h3 className="font-semibold text-charcoal">Done. Point the apps at these contracts</h3>
          <textarea readOnly className={cx(inputCls, "h-36 font-mono text-xs")} value={JSON.stringify(deployment, null, 2)} />
          <Button variant="secondary" onClick={() => { navigator.clipboard?.writeText(json).then(() => setCopied(true)).catch(() => setCopied(false)); }}>
            {copied ? "Copied" : "Copy as one line"}
          </Button>
          <ol className="list-decimal space-y-1 pl-5 text-sm text-charcoal-soft">
            <li><strong>Vercel</strong> → project → Settings → Environment Variables: add <code>NEXT_PUBLIC_DEPLOYMENT_JSON</code> = the copied line, then Deployments → Redeploy (it is inlined at build time).</li>
            <li><strong>Render</strong> → the API service → Environment: add <code>DEPLOYMENT_JSON</code> = the same line. Render restarts the service; the indexer starts reading events from block {deployment.startBlock}.</li>
            <li>Optional, for the repo: save it as <code>contracts/deployments/{TARGET_CHAIN.id}.json</code> and run <code>npm run export-abis</code>.</li>
          </ol>
        </Card>
      )}
    </div>
  );
}
