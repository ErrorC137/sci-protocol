"use client";

import { ConnectButton } from "@rainbow-me/rainbowkit";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { DEPLOYMENT, TARGET_CHAIN } from "@/lib/chain";
import { cx } from "./ui";

const LINKS = [
  ["/discover", "Discover"],
  ["/profile", "Profile"],
  ["/matches", "Matches"],
  ["/raise", "Raise"],
  ["/vault", "Vault"],
] as const;

export function Nav() {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 30_000 });
  const ok = health.data?.status === "ok";
  return (
    <nav className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-bold tracking-tight text-ink">
          <span className="grid h-7 w-7 place-items-center rounded-md bg-brand-600 text-xs text-white">SCI</span>
          <span className="hidden sm:inline">SCI Protocol</span>
        </Link>
        <div className="hidden gap-1 md:flex">
          {LINKS.map(([href, label]) => (
            <Link key={href} href={href}
              className={cx("rounded-md px-3 py-1.5 text-sm font-medium", path?.startsWith(href) ? "bg-brand-50 text-brand-700" : "text-ink-soft hover:bg-slate-100")}>
              {label}
            </Link>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-3">
          <span title={ok ? `API ok · ${health.data?.corpus_size} opportunities · LLM ${health.data?.llm.enabled ? "on" : "off (templates)"}` : "API unreachable"}
            className="hidden items-center gap-1.5 text-xs text-ink-muted lg:flex">
            <span className={cx("h-2 w-2 rounded-full", ok ? "bg-emerald-500" : "bg-rose-500")} />
            {TARGET_CHAIN.name}{!DEPLOYMENT && " (not deployed)"}
          </span>
          <ConnectButton accountStatus="avatar" chainStatus="none" showBalance={false} />
          <button className="rounded-md p-2 text-ink-soft hover:bg-slate-100 md:hidden" onClick={() => setOpen(!open)} aria-label="Menu">☰</button>
        </div>
      </div>
      {open && (
        <div className="flex flex-col border-t border-slate-200 px-4 py-2 md:hidden">
          {LINKS.map(([href, label]) => (
            <Link key={href} href={href} onClick={() => setOpen(false)} className="rounded-md px-3 py-2 text-sm font-medium text-ink-soft hover:bg-slate-100">{label}</Link>
          ))}
        </div>
      )}
    </nav>
  );
}
