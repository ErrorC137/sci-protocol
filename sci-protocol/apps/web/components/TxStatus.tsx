"use client";

import type { TxState } from "@/lib/tx";
import { txUrl } from "@/lib/chain";
import { Spinner } from "./ui";

export function TxStatus({ state }: { state: TxState }) {
  if (state.status === "idle") return null;
  const link = state.hash && txUrl(state.hash);
  return (
    <div className={
      state.status === "error" ? "mt-2 text-sm text-rose-700" : state.status === "done" ? "mt-2 text-sm text-emerald-700" : "mt-2 flex items-center gap-2 text-sm text-ink-muted"
    }>
      {(state.status === "pending" || state.status === "confirming") && <Spinner />}
      {state.status === "pending" && <span>{state.label}: confirm in your wallet…</span>}
      {state.status === "confirming" && <span>{state.label}: waiting for confirmation…</span>}
      {state.status === "done" && <span>✓ {state.label} confirmed.</span>}
      {state.status === "error" && <span>✗ {state.label}: {state.error}</span>}
      {link && <a href={link} target="_blank" rel="noreferrer" className="ml-1 underline">view tx</a>}
    </div>
  );
}
