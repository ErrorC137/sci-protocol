"use client";

import { useEffect, useRef, useState, type ElementType, type ReactNode } from "react";
import { cx } from "@/components/ui";

// Masked line slide-up (expo.out). Text is real DOM and fully visible without JS: lines only start hidden when the
// landing page has put `motion` on <html> (see MotionGate), and GSAP then reveals them as they scroll into view.
export function RevealLines({ lines, as: Tag = "h2", className, lineClassName }: {
  lines: ReactNode[]; as?: ElementType; className?: string; lineClassName?: (i: number) => string | undefined;
}) {
  return (
    <Tag className={className} data-reveal-group>
      {lines.map((l, i) => (
        <span key={i} className="reveal-mask block">
          <span className={cx("reveal-line block", lineClassName?.(i))}>{l}</span>
        </span>
      ))}
    </Tag>
  );
}

// Fades + lifts a block into view (same gating as RevealLines).
export function Reveal({ children, className, delay = 0, as: Tag = "div" }: { children: ReactNode; className?: string; delay?: number; as?: ElementType }) {
  return <Tag className={cx("reveal-block", className)} data-reveal-delay={delay || undefined}>{children}</Tag>;
}

// Counts to `value` (tabular figures) when it scrolls into view, or immediately when `run` flips true.
export function Counter({ value, prefix = "", suffix = "", run, duration = 1200, className }: {
  value: number; prefix?: string; suffix?: string; run?: boolean; duration?: number; className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const [shown, setShown] = useState(value);
  const [visible, setVisible] = useState(false);
  const active = run ?? visible;

  // Server/no-JS render shows the final figure; with motion on, start from 0 so the count-up doesn't jump back.
  useEffect(() => {
    if (document.documentElement.classList.contains("motion")) setShown(0);
  }, []);

  useEffect(() => {
    if (run !== undefined || !ref.current) return;
    const io = new IntersectionObserver(([e]) => e.isIntersecting && setVisible(true), { threshold: 0.6 });
    io.observe(ref.current);
    return () => io.disconnect();
  }, [run]);

  useEffect(() => {
    if (!active) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setShown(value); return; }
    let raf = 0;
    const t0 = performance.now();
    const step = (now: number) => {
      const k = Math.min(1, (now - t0) / duration);
      setShown(Math.round(value * (1 - Math.pow(2, -10 * k))));
      if (k < 1) raf = requestAnimationFrame(step);
      else setShown(value);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [active, value, duration]);

  return <span ref={ref} className={cx("tabular-nums", className)}>{prefix}{shown.toLocaleString("en-US")}{suffix}</span>;
}
