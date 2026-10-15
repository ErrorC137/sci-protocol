"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { Chip, StatusChip, cx } from "@/components/ui";
import { DEPLOYMENT, PROJECT_STATUS } from "@/lib/chain";
import { usdc } from "@/lib/format";
import { useMetadata, useProjects, type ProjectSummary } from "@/lib/hooks";
import { DEMO_DATA, PIPELINE } from "../content";
import { onFrame, store } from "../motion";
import { RevealLines } from "../Reveal";

// Generative thumbnails in brand colours - no stock imagery, no external assets.
function Art({ kind }: { kind: string }) {
  if (kind === "crystal") {
    return (
      <svg viewBox="0 0 160 100" className="h-full w-full" aria-hidden>
        <rect width="160" height="100" fill="#1E2320" />
        {[[50, 52, 26], [86, 44, 34], [116, 62, 20]].map(([x, y, r], i) => (
          <polygon key={i} points={`${x},${y - r} ${x + r * 0.8},${y} ${x},${y + r} ${x - r * 0.8},${y}`}
            fill={i === 1 ? "#D7EB79" : "none"} stroke={i === 1 ? "none" : "#B57856"} strokeWidth="1.5" opacity={i === 1 ? 0.9 : 1} />
        ))}
      </svg>
    );
  }
  if (kind === "flow") {
    return (
      <svg viewBox="0 0 160 100" className="h-full w-full" aria-hidden>
        <rect width="160" height="100" fill="#1E2320" />
        {Array.from({ length: 7 }, (_, i) => (
          <path key={i} d={`M -10 ${20 + i * 10} C 50 ${5 + i * 12}, 100 ${45 + i * 6}, 170 ${25 + i * 9}`} fill="none"
            stroke={i === 3 ? "#D7EB79" : "#A7B8A1"} strokeOpacity={i === 3 ? 1 : 0.35} strokeWidth={i === 3 ? 2 : 1} />
        ))}
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 160 100" className="h-full w-full" aria-hidden>
      <rect width="160" height="100" fill="#1E2320" />
      {Array.from({ length: 6 }, (_, r) => Array.from({ length: 9 }, (_, c) => (
        <circle key={`${r}-${c}`} cx={14 + c * 17 + (r % 2) * 8} cy={14 + r * 15} r={r === 2 && c === 4 ? 5 : 2.2}
          fill={r === 2 && c === 4 ? "#D7EB79" : (r + c) % 3 === 0 ? "#B57856" : "#EDE8DD"} fillOpacity={r === 2 && c === 4 ? 1 : 0.5} />
      )))}
    </svg>
  );
}

function CardShell({ children, art, href }: { children: React.ReactNode; art: string; href?: string }) {
  const body = (
    <article className="flex h-full w-[min(82vw,20rem)] shrink-0 snap-start flex-col overflow-hidden rounded-2xl border border-neutral bg-white transition-colors hover:border-charcoal md:w-[22rem]">
      <div className="aspect-[16/10] w-full"><Art kind={art} /></div>
      <div className="flex flex-1 flex-col gap-3 p-5">{children}</div>
    </article>
  );
  return href ? <Link href={href} className="block h-full">{body}</Link> : body;
}

function Progress({ raised, target, label }: { raised: number; target: number; label: string }) {
  const k = target > 0 ? Math.min(1, raised / target) : 0;
  return (
    <div className="mt-auto">
      <div className="flex items-baseline justify-between text-sm">
        <span className="figure font-semibold text-charcoal">{label}</span>
        <span className="figure text-xs text-charcoal-muted">{Math.round(k * 100)}%</span>
      </div>
      <div className="mt-2 h-1.5 rounded-full bg-charcoal/10"><div className="h-1.5 rounded-full bg-lime-500" style={{ width: `${k * 100}%` }} /></div>
    </div>
  );
}

function LiveCard({ p }: { p: ProjectSummary }) {
  const meta = useMetadata(p.metadataCID);
  return (
    <CardShell art={(["lattice", "crystal", "flow"] as const)[Number(p.id % 3n)]} href={`/raise/${p.id}`}>
      <div className="flex flex-wrap gap-1.5"><Chip tone="dark">Live on testnet</Chip><Chip>TRL {p.trl}</Chip><Chip tone="info">{PROJECT_STATUS[p.status]}</Chip></div>
      <h3 className="font-display text-lg font-semibold text-charcoal">{meta.data?.nickname ?? `Project #${p.id}`}</h3>
      <Progress raised={Number(p.raised) / 1e6} target={Number(p.target) / 1e6} label={`${usdc(p.raised, 0)} / ${usdc(p.target, 0)} mUSDC`} />
    </CardShell>
  );
}

function LiveCards() {
  const projects = useProjects();
  return <>{projects.data?.filter((p) => p.target > 0n).slice(0, 4).map((p) => <LiveCard key={p.id.toString()} p={p} />)}</>;
}

// S6 · Research pipeline (limestone, ~180vh desktop). A horizontal track driven by vertical scroll; real on-chain
// raises (when contracts are deployed) come first, then badged demo cards. Mobile: a native swipe row.
export function Pipeline() {
  const track = useRef<HTMLDivElement>(null);
  useEffect(() => onFrame(() => {
    const el = track.current;
    if (!el || window.innerWidth < 768) { if (el) el.style.transform = ""; return; }
    const overflow = Math.max(0, el.scrollWidth - el.parentElement!.clientWidth);
    el.style.transform = `translate3d(${-(store.pinned.pipeline ?? 0) * overflow}px,0,0)`;
  }), []);

  return (
    <section id="pipeline" data-section="pipeline" data-theme="light" className="relative scroll-mt-16 bg-limestone md:h-[180vh]">
      <div className="py-24 md:sticky md:top-0 md:flex md:h-screen md:flex-col md:justify-center md:overflow-hidden md:py-0">
        <div className="relative z-10 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <p className="eyebrow">{PIPELINE.eyebrow}</p>
          <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
            <RevealLines as="h2" className="max-w-2xl font-display text-3xl font-semibold leading-tight text-charcoal sm:text-5xl" lines={[PIPELINE.title]} />
            <Link href="/raise" className="link text-sm">See every raise</Link>
          </div>
        </div>
        <div className="relative z-10 mx-auto mt-10 w-full max-w-7xl overflow-x-auto px-4 pb-4 sm:px-6 md:overflow-visible lg:px-8 [scrollbar-width:none]">
          <div ref={track} className="flex snap-x snap-mandatory gap-5 will-change-transform md:snap-none">
            {DEPLOYMENT && <LiveCards />}
            {PIPELINE.demo.map((d) => (
              <CardShell key={d.title} art={d.art}>
                <div className="flex flex-wrap gap-1.5">
                  <Chip tone="caution">{DEMO_DATA}</Chip>
                  <Chip>TRL {d.trl}</Chip>
                  {d.status === "Open" ? <Chip>{d.status}</Chip> : <StatusChip status="progress">{d.status}</StatusChip>}
                </div>
                <h3 className="font-display text-lg font-semibold text-charcoal">{d.title}</h3>
                <p className="text-sm text-charcoal-muted">{d.type} · {d.impact}</p>
                <Progress raised={d.raised} target={d.target} label={`$${d.raised.toLocaleString("en-US")} / $${d.target.toLocaleString("en-US")}`} />
              </CardShell>
            ))}
            <div className={cx("flex w-[min(82vw,20rem)] shrink-0 snap-start flex-col justify-center rounded-2xl border border-dashed border-charcoal/30 p-6 md:w-[22rem]")}>
              <p className="font-display text-xl font-semibold text-charcoal">Have TRL 4–6 research?</p>
              <p className="mt-2 text-sm text-charcoal-soft">Describe it once, in non-confidential terms, and see every route to funding.</p>
              <Link href="/profile" className="link mt-4 text-sm">Start a research profile</Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
