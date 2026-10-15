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

// Mounts the fixed 3D canvas only where it pays off: desktop/tablet width (>= 768px), WebGL available, motion
// allowed. It waits until the page is idle so the server-rendered headline is never held up by three.js;
// everywhere else the SVG ring twins stay in place.
export function RingCanvas() {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    const decide = () => setOn(mq.matches && !prefersReducedMotion() && webglOk());
    const w = window as Window & { requestIdleCallback?: (cb: () => void, o?: { timeout: number }) => number };
    const id = w.requestIdleCallback ? w.requestIdleCallback(decide, { timeout: 1500 }) : window.setTimeout(decide, 600);
    mq.addEventListener("change", decide);
    return () => {
      mq.removeEventListener("change", decide);
      if (!w.requestIdleCallback) window.clearTimeout(id);
    };
  }, []);
  return on ? <Scene /> : null;
}
