"use client";

import { ConnectButton } from "@rainbow-me/rainbowkit";
import { Wallet } from "lucide-react";
import { cx } from "./ui";

// RainbowKit's ConnectButton, restyled to the UPLO button system. The not-connected label stays exactly
// "Connect Wallet" (scripts/e2e/smoke.py looks for it).
export function WalletButton({ variant = "lime", className }: { variant?: "lime" | "dark"; className?: string }) {
  const base = "inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-colors";
  const tone = variant === "dark"
    ? "bg-charcoal text-limestone-50 hover:bg-charcoal-800"
    : "bg-lime text-charcoal hover:bg-lime-400";
  return (
    <ConnectButton.Custom>
      {({ account, chain, mounted, openAccountModal, openChainModal, openConnectModal }) => {
        const ready = mounted;
        if (!ready) return <span aria-hidden className={cx(base, tone, "invisible", className)}>Connect Wallet</span>;
        if (!account || !chain) {
          return <button type="button" onClick={openConnectModal} className={cx(base, tone, className)}>Connect Wallet</button>;
        }
        if (chain.unsupported) {
          return <button type="button" onClick={openChainModal} className={cx(base, "bg-error text-white hover:bg-error-700", className)}>Wrong network</button>;
        }
        return (
          <button type="button" onClick={openAccountModal} className={cx(base, tone, "tabular-nums", className)} title={account.address}>
            <Wallet aria-hidden className="h-4 w-4" />{account.displayName}
          </button>
        );
      }}
    </ConnectButton.Custom>
  );
}
