"use client";

import { Menu, Search, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { onFrame, store } from "./landing/motion";
import { Logo } from "./Logo";
import { WalletButton } from "./WalletButton";

// Marketing-site chrome for "/": light nav (logo · links · search · charcoal "Connect Wallet" pill) and the
// charcoal footer. The app pages use AppShell instead.
const NAV: [string, string][] = [
  ["Product", "/#capital-flow"],
  ["For Investors", "/#two-pools"],
  ["For Innovators", "/#pipeline"],
  ["Resources", "/discover"],
  ["About", "/#trust"],
];

const DARK_SECTIONS = new Set(["gap", "flow", "revenue", "trust"]);

export function SiteNav() {
  const [open, setOpen] = useState(false);
  // On the landing page the nav follows the section behind it: charcoal over dark sections.
  const [dark, setDark] = useState(false);
  useEffect(() => onFrame(() => {
    const d = DARK_SECTIONS.has(store.underNav);
    setDark((cur) => (cur === d ? cur : d));
  }), []);
  return (
    <header className={`sticky top-0 z-40 border-b backdrop-blur transition-colors duration-300 ${dark ? "border-charcoal-700 bg-charcoal/90" : "border-neutral/70 bg-limestone/85"}`}>
      <div className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" aria-label="UPLO home"><Logo on={dark ? "dark" : "light"} /></Link>
        <nav aria-label="Main" className={`hidden flex-1 justify-center gap-7 text-sm font-medium md:flex ${dark ? "text-limestone-300" : "text-charcoal-soft"}`}>
          {NAV.map(([label, href]) => <Link key={label} href={href} className={`transition-colors ${dark ? "hover:text-limestone-50" : "hover:text-charcoal"}`}>{label}</Link>)}
        </nav>
        <div className="ml-auto flex items-center gap-2 md:ml-0">
          <Link href="/discover" aria-label="Search opportunities" className={`hidden rounded-full p-2 sm:block ${dark ? "text-limestone-100 hover:bg-white/10" : "text-charcoal hover:bg-charcoal/5"}`}>
            <Search className="h-4 w-4" />
          </Link>
          <WalletButton variant={dark ? "lime" : "dark"} />
          <button className={`rounded-lg p-2 md:hidden ${dark ? "text-limestone-100 hover:bg-white/10" : "text-charcoal hover:bg-charcoal/5"}`} onClick={() => setOpen(!open)}
            aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open}>
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>
      {open && (
        <nav aria-label="Main" className={`border-t px-4 pb-4 md:hidden ${dark ? "border-charcoal-700" : "border-neutral"}`}>
          {NAV.map(([label, href]) => (
            <Link key={label} href={href} onClick={() => setOpen(false)}
              className={`block rounded-lg px-2 py-2.5 text-sm font-medium ${dark ? "text-limestone-100 hover:bg-white/10" : "text-charcoal hover:bg-charcoal/5"}`}>{label}</Link>
          ))}
        </nav>
      )}
    </header>
  );
}

const COLUMNS: [string, [string, string][]][] = [
  ["Platform", [["Discover funding", "/discover"], ["Research profile", "/profile"], ["Matches", "/matches"]]],
  ["Capital", [["Milestone raises", "/raise"], ["Open a raise", "/raise/new"], ["Private vault", "/vault"]]],
  ["Company", [["How it works", "/#capital-flow"], ["Two pools", "/#two-pools"], ["Why trust it", "/#trust"]]],
];

export function SiteFooter() {
  return (
    <footer className="bg-charcoal text-limestone-300">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-[1.4fr_repeat(3,1fr)] lg:px-8">
        <div className="space-y-3">
          <Logo on="dark" />
          <p className="max-w-xs text-sm text-limestone-400">Today&apos;s Capital. <span className="text-lime">Tomorrow&apos;s Breakthroughs.</span></p>
        </div>
        {COLUMNS.map(([title, links]) => (
          <div key={title}>
            <p className="eyebrow text-limestone-400">{title}</p>
            <ul className="mt-3 space-y-2 text-sm">
              {links.map(([label, href]) => <li key={label}><Link href={href} className="transition-colors hover:text-lime">{label}</Link></li>)}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-charcoal-700">
        <div className="mx-auto max-w-7xl space-y-1 px-4 py-6 text-xs text-limestone-400 sm:px-6 lg:px-8">
          <p>Testnet only · no real value · not a securities offering · centralized attestor (decentralizing it is future work).</p>
          <p>Hackathon concept, demo data where marked.</p>
        </div>
      </div>
    </footer>
  );
}
