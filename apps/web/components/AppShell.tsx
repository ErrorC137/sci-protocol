"use client";

import { useQuery } from "@tanstack/react-query";
import { Compass, Landmark, LayoutDashboard, Lock, Menu, Rocket, ShieldCheck, X, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { api } from "@/lib/api";
import { DEPLOYMENT, TARGET_CHAIN } from "@/lib/chain";
import { Logo } from "./Logo";
import { WalletButton } from "./WalletButton";
import { cx } from "./ui";

// UPLO information architecture. Each section maps onto existing features where they exist (Innovation Pool =
// the milestone-escrow raises, Research Pipeline = discover/profile/matches/apply/evidence); Overview and
// Commercial Finance are front-end demo pages. `match` lists every path prefix that lights the item up.
interface NavItem { href: string; label: string; icon: LucideIcon; match: string[]; sub?: [string, string][] }

const LINKS: NavItem[] = [
  { href: "/overview", label: "Overview", icon: LayoutDashboard, match: ["/overview"] },
  { href: "/commercial-finance", label: "Commercial Finance", icon: Landmark, match: ["/commercial-finance"] },
  { href: "/raise", label: "Innovation Pool", icon: Rocket, match: ["/raise"] },
  {
    href: "/discover", label: "Research Pipeline", icon: Compass, match: ["/discover", "/profile", "/matches", "/apply", "/evidence"],
    sub: [["/discover", "Discover"], ["/profile", "Profile"], ["/matches", "Matches"], ["/evidence", "Evidence"]],
  },
  { href: "/validation", label: "Validation", icon: ShieldCheck, match: ["/validation"] },
  { href: "/vault", label: "Vault", icon: Lock, match: ["/vault"] },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const path = usePathname() ?? "";
  return (
    <ul className="space-y-1">
      {LINKS.map(({ href, label, icon: Icon, match, sub }) => {
        const active = match.some((m) => path.startsWith(m));
        return (
          <li key={href}>
            <Link href={href} onClick={onNavigate} aria-current={active && !sub ? "page" : undefined}
              className={cx("flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active ? "bg-lime text-charcoal" : "text-limestone-300 hover:bg-charcoal-800 hover:text-limestone-50")}>
              <Icon aria-hidden className="h-4 w-4" strokeWidth={1.75} />{label}
            </Link>
            {sub && active && (
              <ul className="ml-[1.4rem] mt-1 space-y-0.5 border-l border-charcoal-700 pl-3">
                {sub.map(([h, l]) => {
                  const on = path.startsWith(h);
                  return (
                    <li key={h}>
                      <Link href={h} onClick={onNavigate} aria-current={on ? "page" : undefined}
                        className={cx("block rounded-md px-2 py-1 text-[13px] transition-colors",
                          on ? "font-semibold text-lime" : "text-limestone-400 hover:text-limestone-50")}>{l}</Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function NetworkStatus() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 30_000 });
  const ok = health.data?.status === "ok";
  return (
    <p className="flex items-center gap-2 text-xs text-limestone-400"
      title={ok ? `API ok · ${health.data?.corpus_size} opportunities · LLM ${health.data?.llm.enabled ? "on" : "off (templates)"}` : "API unreachable"}>
      <span className={cx("h-2 w-2 rounded-full", ok ? "bg-lime" : health.isLoading ? "bg-limestone-400" : "bg-error")} />
      <span>{ok ? "API online" : health.isLoading ? "Connecting…" : "API unreachable"}</span>
      <span aria-hidden>·</span>
      <span>{TARGET_CHAIN.name}{!DEPLOYMENT && <> (<Link href="/setup" className="underline">not deployed</Link>)</>}</span>
    </p>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const path = usePathname();
  useEffect(() => setOpen(false), [path]);

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[15rem_1fr]">
      {/* Desktop sidebar */}
      <aside className="hidden bg-charcoal lg:block">
        <div className="sticky top-0 flex h-screen flex-col px-4 py-6">
          <Link href="/" className="px-3" aria-label="UPLO home"><Logo on="dark" /></Link>
          <nav aria-label="App" className="mt-10 flex-1"><NavLinks /></nav>
          <div className="space-y-3 border-t border-charcoal-700 px-3 pt-4">
            <NetworkStatus />
            <p className="text-[11px] leading-snug text-limestone-400">Testnet only · mock stablecoin · no real value</p>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-col">
        {/* Mobile top bar */}
        <header className="sticky top-0 z-30 flex items-center gap-3 bg-charcoal px-4 py-3 lg:hidden">
          <Link href="/" aria-label="UPLO home"><Logo on="dark" /></Link>
          <div className="ml-auto"><WalletButton /></div>
          <button className="rounded-lg p-2 text-limestone-100 hover:bg-charcoal-800" onClick={() => setOpen(!open)}
            aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open}>
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </header>
        {open && (
          <nav aria-label="App" className="sticky top-[60px] z-20 space-y-4 bg-charcoal px-4 pb-5 lg:hidden">
            <NavLinks onNavigate={() => setOpen(false)} />
            <NetworkStatus />
          </nav>
        )}

        {/* Desktop top bar */}
        <div className="hidden items-center justify-end gap-4 px-10 pt-6 lg:flex">
          <WalletButton />
        </div>

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 pb-16 pt-6 sm:px-6 lg:px-10 lg:pt-2">{children}</main>

        <footer className="border-t border-neutral px-4 py-6 text-xs text-charcoal-muted sm:px-6 lg:px-10">
          Testnet only · no real value · not a securities offering · centralized attestor (decentralizing it is future work)
        </footer>
      </div>
    </div>
  );
}
