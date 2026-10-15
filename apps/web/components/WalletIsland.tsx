"use client";

import { useEffect } from "react";
import { Providers } from "@/app/providers";
import { WalletButton } from "./WalletButton";

// The full wallet stack (wagmi + RainbowKit + connectors) as a self-contained island, for pages that don't
// otherwise need it. Loaded on demand by LandingWallet; tells it when it's on screen so the swap is seamless.
export default function WalletIsland({ variant, autoOpen, onReady }: { variant: "lime" | "dark"; autoOpen: boolean; onReady: () => void }) {
  useEffect(() => { const t = window.setTimeout(onReady, 60); return () => window.clearTimeout(t); }, [onReady]);
  return <Providers><WalletButton variant={variant} autoOpen={autoOpen} /></Providers>;
}
