import { cx } from "@/components/ui";

// The segmented "Circular O" as SVG - the 2D twin of the 3D ring. Used for the preloader, mobile, reduced-motion
// and no-WebGL fallbacks. It is a story device (one segment per capital-flow stage), not the UPLO logo.

const TAU = Math.PI * 2;
const SIZE = 200, C = SIZE / 2, RO = 92, RI = 62, GAP = 0.07;

function sector(c: number, ro: number, ri: number, a0: number, a1: number) {
  const p = (r: number, a: number) => `${(c + r * Math.cos(a)).toFixed(2)} ${(c + r * Math.sin(a)).toFixed(2)}`;
  const large = a1 - a0 > Math.PI ? 1 : 0;
  return `M ${p(ro, a0)} A ${ro} ${ro} 0 ${large} 1 ${p(ro, a1)} L ${p(ri, a1)} A ${ri} ${ri} 0 ${large} 0 ${p(ri, a0)} Z`;
}

/** Path of segment `i` of `segments`, clockwise from 12 o'clock, in a 200x200 viewBox. */
export function sectorPath(i: number, segments: number) {
  const step = TAU / segments;
  const a0 = -Math.PI / 2 + i * step + GAP / 2;
  return sector(C, RO, RI, a0, a0 + step - GAP);
}

export function RingSvg({
  segments = 6, lit = 1, drawn = segments, tone = "light", glow = false, className, title,
}: {
  segments?: number;
  /** how many segments glow lime, counting clockwise from the top */
  lit?: number;
  /** how many segments are drawn at all (preloader) */
  drawn?: number;
  tone?: "light" | "dark";
  glow?: boolean;
  className?: string;
  title?: string;
}) {
  const unlit = tone === "dark" ? "rgba(237,232,221,0.16)" : "#1E2320";
  return (
    <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className={cx("overflow-visible", className)} role={title ? "img" : undefined}
      aria-label={title} aria-hidden={title ? undefined : true}>
      {glow && (
        <defs>
          <filter id="ring-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="5" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
      )}
      <g filter={glow ? "url(#ring-glow)" : undefined}>
        {Array.from({ length: segments }, (_, i) => {
          const on = i < lit;
          return (
            <path key={i} d={sectorPath(i, segments)}
              fill={on ? "#D7EB79" : unlit}
              style={{ opacity: i < drawn ? 1 : 0, transition: "fill 600ms cubic-bezier(.16,1,.3,1), opacity 350ms ease-out" }} />
          );
        })}
      </g>
    </svg>
  );
}
