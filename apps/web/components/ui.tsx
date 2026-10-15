import Link from "next/link";
import type { ReactNode } from "react";

export function cx(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("rounded-xl border border-slate-200 bg-white p-5 shadow-sm", className)}>{children}</div>;
}

export function PageHeader({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: ReactNode }) {
  return (
    <header className="mb-6">
      {eyebrow && <p className="text-xs font-semibold uppercase tracking-wider text-brand-600">{eyebrow}</p>}
      <h1 className="mt-1 text-2xl font-bold tracking-tight text-ink sm:text-3xl">{title}</h1>
      {children && <div className="mt-2 max-w-3xl text-ink-soft">{children}</div>}
    </header>
  );
}

const CHIP = {
  slate: "bg-slate-100 text-slate-700",
  green: "bg-emerald-100 text-emerald-800",
  amber: "bg-amber-100 text-amber-900",
  red: "bg-rose-100 text-rose-800",
  blue: "bg-brand-100 text-brand-700",
  violet: "bg-violet-100 text-violet-800",
};

export function Chip({ children, tone = "slate", title }: { children: ReactNode; tone?: keyof typeof CHIP; title?: string }) {
  return (
    <span title={title} className={cx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium", CHIP[tone])}>
      {children}
    </span>
  );
}

const BTN = {
  primary: "bg-brand-600 text-white hover:bg-brand-700 disabled:bg-slate-300",
  secondary: "border border-slate-300 bg-white text-ink hover:bg-slate-50 disabled:text-slate-400",
  danger: "bg-rose-600 text-white hover:bg-rose-700 disabled:bg-slate-300",
  ghost: "text-brand-700 hover:bg-brand-50 disabled:text-slate-400",
};

export function Button({
  children, onClick, variant = "primary", disabled, type = "button", className, href,
}: {
  children: ReactNode; onClick?: () => void; variant?: keyof typeof BTN; disabled?: boolean;
  type?: "button" | "submit"; className?: string; href?: string;
}) {
  const cls = cx("inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed", BTN[variant], className);
  if (href) return <Link href={href} className={cls}>{children}</Link>;
  return <button type={type} onClick={onClick} disabled={disabled} className={cls}>{children}</button>;
}

export function Spinner({ className }: { className?: string }) {
  return <span className={cx("inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent", className)} aria-hidden />;
}

export function PrivacyBanner() {
  return (
    <div className="flex gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
      <span aria-hidden className="text-lg">🔒</span>
      <p>
        <strong>We never ask for your method, composition, data, or any detail that could affect patentability.</strong>{" "}
        Matching runs on category and stage only.
      </p>
    </div>
  );
}

export function Notice({ tone = "amber", children }: { tone?: "amber" | "blue" | "red" | "green"; children: ReactNode }) {
  const t = {
    amber: "border-amber-200 bg-amber-50 text-amber-900",
    blue: "border-brand-100 bg-brand-50 text-brand-700",
    red: "border-rose-200 bg-rose-50 text-rose-900",
    green: "border-emerald-200 bg-emerald-50 text-emerald-900",
  }[tone];
  return <div className={cx("rounded-lg border p-3 text-sm", t)}>{children}</div>;
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <Card className="text-center">
      <p className="font-semibold text-ink">{title}</p>
      {children && <div className="mt-2 text-sm text-ink-muted">{children}</div>}
    </Card>
  );
}

export function Bar({ value, className }: { value: number; className?: string }) {
  return (
    <div className="h-1.5 w-full rounded-full bg-slate-100">
      <div className={cx("h-1.5 rounded-full bg-brand-500", className)} style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
    </div>
  );
}

export function Label({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="mb-1.5">
      <span className="text-sm font-semibold text-ink">{children}</span>
      {hint && <p className="text-xs text-ink-muted">{hint}</p>}
    </div>
  );
}

export const inputCls =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100";

export function Toggle({ checked, onChange, children, disabled }: { checked: boolean; onChange: (v: boolean) => void; children: ReactNode; disabled?: boolean }) {
  return (
    <label className={cx("flex cursor-pointer items-start gap-2 rounded-lg border px-3 py-2 text-sm",
      checked ? "border-brand-500 bg-brand-50" : "border-slate-200 bg-white hover:border-slate-300", disabled && "opacity-50")}>
      <input type="checkbox" className="mt-0.5 accent-brand-600" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      <span>{children}</span>
    </label>
  );
}
