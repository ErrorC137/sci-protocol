"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { prefersReducedMotion } from "./motion";

const Scene = dynamic(() => import("./three/Scene"), { ssr: false });

function webglOk() {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}

const INTENT = ["pointermove", "pointerdown", "wheel", "scroll", "touchstart", "keydown"] as const;

// Mounts the fixed 3D canvas only where it pays off - width >= 768px, WebGL available, motion allowed - and only
// once the visitor shows intent (first pointer move, scroll, touch or key). Until then the SVG ring twins hold
// the exact same spots, and the 3D cross-fades in over them. Loading three.js on intent rather than on idle keeps
// it off the critical path entirely: the headline paints first, and the main thread is quiet while the page settles.
export function RingCanvas() {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    if (!mq.matches || prefersReducedMotion() || !webglOk()) return;
    const go = () => { cleanup(); setOn(true); };
    const cleanup = () => INTENT.forEach((e) => window.removeEventListener(e, go));
    INTENT.forEach((e) => window.addEventListener(e, go, { passive: true, once: true }));
    // Arriving already scrolled (reload mid-page, anchor link) counts as intent.
    if (window.scrollY > 0) go();
    return cleanup;
  }, []);
  return on ? <Scene /> : null;
}
