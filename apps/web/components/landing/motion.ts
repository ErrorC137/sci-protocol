// Scroll state for the landing page. One rAF loop measures the sections ([data-section], in DOM order) and
// publishes:
//   store.t           continuous position: section i spans [i, i+1) while the viewport centre passes through it
//   store.pinned[id]  0..1 progress through a sticky ("pinned") section: top hits top -> bottom hits bottom
//   store.mouse       normalised pointer position (-1..1), for parallax
//   store.underNav    the section currently behind the sticky nav (it turns charcoal over dark sections)
// The 3D scene reads it inside useFrame; DOM effects subscribe with onFrame(). Nothing here re-renders React.

export const SECTION_IDS = ["hero", "gap", "flow", "pools", "revenue", "pipeline", "trust", "finale"] as const;
export type SectionId = (typeof SECTION_IDS)[number];

export const store = {
  t: 0,
  pinned: {} as Partial<Record<SectionId, number>>,
  mouse: { x: 0, y: 0 },
  vh: 1,
  underNav: "hero" as SectionId,
};

type Box = { id: SectionId; top: number; height: number };
let boxes: Box[] = [];
const subs = new Set<() => void>();
let raf = 0;
let running = false;
let lastY = -1;
let dirty = true; // set by measure() and pointer moves; scroll changes are detected directly

export function onFrame(fn: () => void) {
  subs.add(fn);
  return () => { subs.delete(fn); };
}

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

export function measure() {
  const y = window.scrollY;
  boxes = Array.from(document.querySelectorAll<HTMLElement>("[data-section]")).map((el) => {
    const r = el.getBoundingClientRect();
    return { id: el.dataset.section as SectionId, top: r.top + y, height: r.height };
  });
  store.vh = window.innerHeight;
  dirty = true;
}

function tick() {
  raf = requestAnimationFrame(tick);
  const y = window.scrollY;
  if (y === lastY && !dirty) return; // nothing moved: no work this frame
  lastY = y;
  dirty = false;
  const vh = store.vh, mid = y + vh / 2;
  let t = 0;
  for (let i = 0; i < boxes.length; i++) {
    const b = boxes[i];
    if (mid >= b.top) t = i + clamp01((mid - b.top) / b.height);
    store.pinned[b.id] = b.height > vh ? clamp01((y - b.top) / (b.height - vh)) : clamp01((mid - b.top) / b.height);
    if (y + 32 >= b.top && y + 32 < b.top + b.height) store.underNav = b.id;
  }
  store.t = t;
  subs.forEach((fn) => fn());
}

export function startScrollLoop() {
  if (running) return () => {};
  running = true;
  lastY = -1;
  measure();
  const onResize = () => measure();
  const onMove = (e: PointerEvent) => {
    store.mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    store.mouse.y = (e.clientY / window.innerHeight) * 2 - 1;
    dirty = true;
  };
  window.addEventListener("resize", onResize);
  window.addEventListener("pointermove", onMove, { passive: true });
  const ro = new ResizeObserver(onResize);
  ro.observe(document.body);
  raf = requestAnimationFrame(tick);
  return () => {
    running = false;
    cancelAnimationFrame(raf);
    window.removeEventListener("resize", onResize);
    window.removeEventListener("pointermove", onMove);
    ro.disconnect();
  };
}

export function prefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
