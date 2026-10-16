import { ArrowRight, Check, CircleCheck, CircleDashed, Lock } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

export function cx(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

// White on limestone, thin neutral border, no shadow (brand brief §6). `dark` is for charcoal "night" panels;
// `danger` / `positive` tint the whole card (pass a tone rather than overriding bg-/border- via className).
const CARD = {
  light: "border-neutral bg-white",
  dark: "border-charcoal-700 bg-charcoal text-limestone-50",
  danger: "border-error-200 bg-error-50",
  positive: "border-lime-300 bg-lime-50",
};

export function Card({ children, className, tone = "light" }: { children: ReactNode; className?: string; tone?: keyof typeof CARD }) {
  return <div className={cx("rounded-xl border p-5", CARD[tone], className)}>{children}</div>;
}

export function PageHeader({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: ReactNode }) {
  return (
    <header className="mb-8">
      {eyebrow && <p className="eyebrow flex items-center gap-2"><span aria-hidden className="h-1.5 w-1.5 rounded-full bg-lime-500" />{eyebrow}</p>}
      <h1 className="mt-2 text-3xl font-semibold leading-tight tracking-tight text-charcoal sm:text-4xl">{title}</h1>
      {children && <div className="mt-3 max-w-3xl text-[15px] leading-relaxed text-charcoal-soft">{children}</div>}
    </header>
  );
}

// Meaning, not colour: every chip also carries text, so status never relies on colour alone.
const CHIP = {
  neutral: "bg-limestone-100 text-charcoal-soft ring-1 ring-inset ring-neutral",
  positive: "bg-lime-100 text-lime-800 ring-1 ring-inset ring-lime-300",
  caution: "bg-copper-50 text-copper-700 ring-1 ring-inset ring-copper-200",
  danger: "bg-error-50 text-error-700 ring-1 ring-inset ring-error-200",
  info: "bg-sage-50 text-sage-700 ring-1 ring-inset ring-sage-200",
  dark: "bg-charcoal text-limestone-50",
};
export type ChipTone = keyof typeof CHIP;

export function Chip({ children, tone = "neutral", title }: { children: ReactNode; tone?: ChipTone; title?: string }) {
  return (
    <span title={title} className={cx("inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium", CHIP[tone])}>
      {children}
    </span>
  );
}

// The three status chips from the brand board: Verified (lime fill + check circle), In Progress (grey fill +
// dashed circle), Completed (grey fill + solid charcoal check circle). Text always present - never colour alone.
export function StatusChip({ status, children }: { status: "verified" | "progress" | "completed"; children?: ReactNode }) {
  const s = {
    verified: { cls: "bg-lime text-charcoal", icon: <CircleCheck className="h-3.5 w-3.5" strokeWidth={2} />, label: "Verified" },
    progress: { cls: "bg-limestone-200 text-charcoal ring-1 ring-inset ring-neutral", icon: <CircleDashed className="h-3.5 w-3.5" />, label: "In Progress" },
    completed: {
      cls: "bg-limestone-200 text-charcoal ring-1 ring-inset ring-neutral",
      icon: <span className="grid h-3.5 w-3.5 place-items-center rounded-full bg-charcoal text-limestone-50"><Check className="h-2.5 w-2.5" strokeWidth={3.5} /></span>,
      label: "Completed",
    },
  }[status];
  return (
    <span className={cx("inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold", s.cls)}>
      {s.icon}{children ?? s.label}
    </span>
  );
}

const BTN = {
  primary: "bg-lime text-charcoal hover:bg-lime-400 active:bg-lime-500 disabled:bg-neutral disabled:text-charcoal-muted",
  secondary: "border border-charcoal/70 bg-white/60 text-charcoal hover:bg-white active:bg-charcoal/10 disabled:border-neutral disabled:text-charcoal-muted",
  dark: "bg-charcoal text-limestone-50 hover:bg-charcoal-800 active:bg-charcoal-700 disabled:bg-neutral disabled:text-charcoal-muted",
  danger: "bg-error text-white hover:bg-error-700 disabled:bg-neutral disabled:text-charcoal-muted",
  ghost: "text-charcoal hover:bg-charcoal/5 active:bg-charcoal/10 disabled:text-charcoal-muted",
};

export function Button({
  children, onClick, variant = "primary", disabled, type = "button", className, href, arrow,
}: {
  children: ReactNode; onClick?: () => void; variant?: keyof typeof BTN; disabled?: boolean;
  type?: "button" | "submit"; className?: string; href?: string; arrow?: boolean;
}) {
  const cls = cx(
    "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-lg px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed",
    BTN[variant], className,
  );
  const body = <>{children}{arrow && <ArrowRight aria-hidden className="h-4 w-4" />}</>;
  if (href) return <Link href={href} className={cls}>{body}</Link>;
  return <button type={type} onClick={onClick} disabled={disabled} className={cls}>{body}</button>;
}

// Round outline button with an arrow (brand board, UI elements).
export function IconButton({ href, label, className }: { href: string; label: string; className?: string }) {
  return (
    <Link href={href} aria-label={label}
      className={cx("grid h-10 w-10 place-items-center rounded-full border border-charcoal text-charcoal transition-colors hover:bg-lime hover:border-lime", className)}>
      <ArrowRight aria-hidden className="h-4 w-4" />
    </Link>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <span className={cx("inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent", className)} aria-hidden />;
}

export function PrivacyBanner() {
  return (
    <div className="flex gap-3 rounded-xl bg-charcoal p-4 text-sm text-limestone-100">
      <span aria-hidden className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-lime text-charcoal"><Lock className="h-4 w-4" /></span>
      <p className="self-center">
        <strong className="text-limestone-50">We never ask for your method, composition, data, or any detail that could affect patentability.</strong>{" "}
        Matching runs on category and stage only.
      </p>
    </div>
  );
}

const NOTICE = {
  caution: "border-copper-200 bg-copper-50 text-copper-700",
  info: "border-neutral border-l-lime-500 border-l-4 bg-white text-charcoal-soft",
  danger: "border-error-200 bg-error-50 text-error-700",
  positive: "border-lime-300 bg-lime-50 text-lime-800",
};

export function Notice({ tone = "caution", children }: { tone?: keyof typeof NOTICE; children: ReactNode }) {
  return <div className={cx("rounded-lg border p-3 text-sm", NOTICE[tone])}>{children}</div>;
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <Card className="text-center">
      <p className="font-display font-semibold text-charcoal">{title}</p>
      {children && <div className="mt-2 text-sm text-charcoal-muted">{children}</div>}
    </Card>
  );
}

// Progress: lime fill on a charcoal-tinted track. Callers always print the value as text too.
export function Bar({ value, className, tone = "lime" }: { value: number; className?: string; tone?: "lime" | "copper" }) {
  return (
    <div className="h-1.5 w-full rounded-full bg-charcoal/10">
      <div className={cx("h-1.5 rounded-full", tone === "copper" ? "bg-copper" : "bg-lime-500", className)}
        style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
    </div>
  );
}

export function Label({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="mb-1.5">
      <span className="text-sm font-semibold text-charcoal">{children}</span>
      {hint && <p className="text-xs text-charcoal-muted">{hint}</p>}
    </div>
  );
}

export const inputCls =
  "w-full rounded-lg border border-neutral bg-white px-3 py-2 text-sm text-charcoal placeholder:text-charcoal-muted/70 focus:border-charcoal focus:outline-none focus:ring-2 focus:ring-lime disabled:bg-limestone-100";

// Selectable tile (checkbox). Selected = charcoal border on a lime wash.
export const tileCls = (on: boolean) =>
  cx("rounded-lg border text-sm transition-colors", on ? "border-charcoal bg-lime-50" : "border-neutral bg-white hover:border-charcoal/40");

export function Toggle({ checked, onChange, children, disabled }: { checked: boolean; onChange: (v: boolean) => void; children: ReactNode; disabled?: boolean }) {
  return (
    <label className={cx("flex cursor-pointer items-start gap-2 px-3 py-2", tileCls(checked), disabled && "cursor-not-allowed opacity-50")}>
      <input type="checkbox" className="mt-0.5 accent-charcoal" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      <span>{children}</span>
    </label>
  );
}
