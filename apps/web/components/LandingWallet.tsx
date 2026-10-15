"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import { cx } from "./ui";

// "Connect Wallet" for the landing page without paying for the wallet stack up front. A plain button renders
// first; wagmi + RainbowKit load on hover / focus / click (a click also opens the connect modal once loaded),
// or straight away when this browser has connected before, so a returning user sees their account.
const base = "inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-colors";
const tones = { lime: "bg-lime text-charcoal hover:bg-lime-400", dark: "bg-charcoal text-limestone-50 hover:bg-charcoal-800" };

export function LandingWallet({ variant }: { variant: "lime" | "dark" }) {
  const [load, setLoad] = useState(false);
  const [open, setOpen] = useState(false);
  const [ready, setReady] = useState(false);
  const onReady = useCallback(() => setReady(true), []);

  useEffect(() => {
    try { if (localStorage.getItem("wagmi.recentConnectorId")) setLoad(true); } catch { /* storage blocked */ }
  }, []);

  const placeholder = (
    <button type="button" className={cx(base, tones[variant])}
      onPointerEnter={() => setLoad(true)} onFocus={() => setLoad(true)} onClick={() => { setLoad(true); setOpen(true); }}>
      Connect Wallet
    </button>
  );
  if (!load) return placeholder;
  // Plain button stays visible until the island has mounted, then the island takes its place.
  return (
    <>
      {!ready && placeholder}
      <span className={ready ? "contents" : "hidden"}><IslandImpl variant={variant} autoOpen={open} onReady={onReady} /></span>
    </>
  );
}

const IslandImpl = dynamic(() => import("./WalletIsland"), { ssr: false });
