"use client";

import { Environment, Lightformer } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import { BloomEffect } from "postprocessing";
import type React from "react";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { FLOW } from "../content";
import { SECTION_IDS, store } from "../motion";
import { Monolith } from "./Monolith";
import { Ring, SEGMENTS, type RingHandles } from "./Ring";
import { Stations } from "./Stations";

const DARK = new Set(["gap", "flow", "revenue", "trust"]);
const PHASES = FLOW.length + 1;
const damp = THREE.MathUtils.damp;

type Slot = "hero" | "gap" | "flow" | "finale";
// Ring diameter (3 units) as a share of its slot; the hero slot is sized for the whole monolith (4.6 units tall).
const FIT: Record<Slot, number> = { hero: 0.95 / 4.6, gap: 0.8 / 3, flow: 0.82 / 3, finale: 0.78 / 3 };

// Reads the DOM ring slots every frame, projects the active one into world space, and eases the ring there.
// The monolith is pinned to the hero slot, so it scrolls away with the page while the ring flies on.
function Rig() {
  const ring = useRef<THREE.Group>(null);
  const mono = useRef<THREE.Group>(null);
  const bloom = useRef<BloomEffect>(null);
  const handles = useMemo<RingHandles>(() => ({ lime: [] }), []);
  const slots = useRef<HTMLElement[]>([]);
  const lit = useRef(1);
  const flowPhase = useRef(0);
  const placed = useRef(false);
  const { camera } = useThree();

  useEffect(() => {
    const find = () => { slots.current = Array.from(document.querySelectorAll<HTMLElement>("[data-ring-slot]")); };
    find();
    window.addEventListener("resize", find);
    return () => window.removeEventListener("resize", find);
  }, []);

  useFrame((state, dt) => {
    const g = ring.current, m = mono.current;
    if (!g || !m) return;
    dt = Math.min(dt, 0.1);
    const W = window.innerWidth, H = window.innerHeight;
    const vp = state.viewport.getCurrentViewport(camera, [0, 0, 0]);
    const t = state.clock.elapsedTime;

    // Project slots to world space
    let active: { id: Slot; x: number; y: number; s: number } | null = null;
    let best = Infinity;
    for (const el of slots.current) {
      const r = el.getBoundingClientRect();
      // The slot belongs to the section it sits in (React renders the bare data-ring-slot attribute as "true").
      const id = el.closest<HTMLElement>("[data-section]")?.dataset.section as Slot;
      if (!(id in FIT)) continue;
      const x = ((r.left + r.width / 2) / W - 0.5) * vp.width;
      const y = -((r.top + r.height / 2) / H - 0.5) * vp.height;
      const size = Math.min(r.width / W * vp.width, r.height / H * vp.height);
      if (id === "hero") {
        m.position.set(x, y, 0);
        m.scale.setScalar(size * FIT.hero);
        m.visible = r.bottom > -H * 0.2 && r.top < H * 1.2;
      }
      if (r.width === 0 || r.bottom < H * 0.12 || r.top > H * 0.88) continue;
      const d = Math.abs(r.top + r.height / 2 - H / 2);
      if (d < best) { best = d; active = { id, x, y, s: size * FIT[id] }; }
    }

    // Story state: how many segments are lit, how strongly they glow, where the ring faces.
    const p = store.pinned.flow ?? 0;
    flowPhase.current = Math.min(PHASES - 1, Math.floor(p * PHASES * 0.999));
    const mx = store.mouse.x, my = store.mouse.y, k = 0.035; // ±2° parallax
    let L = lit.current, glow = 0.35, rx = 0, ry = 0, rz = 0, z = 0.15;
    switch (active?.id) {
      case "hero": L = 1; rx = 0.04 + my * k; ry = -0.32 + mx * k; z = 0.12; break;
      case "gap": L = 0; rx = 0.55; ry = 0.25; rz = t * 0.15; break;
      case "flow":
        L = flowPhase.current + 1;
        glow = flowPhase.current === PHASES - 1 ? 0.8 + Math.sin(t * 2) * 0.15 : 0.4;
        ry = -0.65 + p * 1.3 + mx * k; rx = 0.12 + Math.sin(p * Math.PI * 2) * 0.18 + my * k; rz = -flowPhase.current * 0.1;
        break;
      case "finale": L = SEGMENTS; glow = 0.45 + Math.sin(t * 1.6) * 0.08; rx = my * k; ry = mx * k; rz = t * 0.06; z = -0.8; break;
    }
    lit.current = L;

    if (active && !placed.current) {
      // First frame: start in place rather than flying in from the centre of the screen.
      placed.current = true;
      g.position.set(active.x, active.y, z);
      g.scale.setScalar(active.s);
    }
    if (active) {
      g.position.x = damp(g.position.x, active.x, 3.2, dt);
      g.position.y = damp(g.position.y, active.y + Math.sin(t * 0.8) * 0.03 * active.s, 3.2, dt);
      g.position.z = damp(g.position.z, z, 3.2, dt);
      g.scale.setScalar(damp(g.scale.x, active.s, 3.2, dt));
    } else {
      g.scale.setScalar(damp(g.scale.x, 0, 4, dt)); // between set pieces the ring bows out
    }
    g.rotation.x = damp(g.rotation.x, rx, 2.6, dt);
    g.rotation.y = damp(g.rotation.y, ry, 2.6, dt);
    g.rotation.z = damp(g.rotation.z, rz, 2.6, dt);
    g.visible = g.scale.x > 0.002;

    handles.lime.forEach((mat, i) => {
      const on = i < L ? 1 : 0;
      mat.opacity = damp(mat.opacity, on, 4, dt);
      mat.emissiveIntensity = mat.opacity * glow;
    });

    // Bloom stays subtle on light sections.
    const sec = SECTION_IDS[Math.min(SECTION_IDS.length - 1, Math.floor(store.t))];
    if (bloom.current) bloom.current.intensity = damp(bloom.current.intensity, DARK.has(sec) ? 0.75 : 0.22, 3, dt);

    camera.position.x = damp(camera.position.x, mx * 0.12, 2, dt);
    camera.position.y = damp(camera.position.y, -my * 0.08, 2, dt);
    camera.lookAt(0, 0, 0);
  });

  return (
    <>
      <Monolith ref={mono} />
      <group ref={ring}>
        <Ring handles={handles} />
        <Stations phase={flowPhase} />
      </group>
      <EffectComposer multisampling={4}>
        {/* @react-three/postprocessing v2 types this ref as the class, not the instance it actually receives */}
        <Bloom ref={bloom as unknown as React.Ref<typeof BloomEffect>} mipmapBlur luminanceThreshold={1.02} luminanceSmoothing={0.12} intensity={0.22} radius={0.5} />
      </EffectComposer>
    </>
  );
}

function Ready() {
  // Hide the SVG fallbacks only once the first real frame has been drawn.
  const done = useRef(false);
  useFrame(() => {
    if (done.current) return;
    done.current = true;
    requestAnimationFrame(() => document.documentElement.classList.add("ring-3d"));
  });
  useEffect(() => () => document.documentElement.classList.remove("ring-3d"), []);
  return null;
}

export default function Scene() {
  return (
    <Canvas
      className="!fixed inset-0 !h-screen !w-screen"
      style={{ position: "fixed", inset: 0, zIndex: 5, pointerEvents: "none" }}
      dpr={[1, 1.75]}
      shadows
      camera={{ position: [0, 0, 10], fov: 35, near: 0.1, far: 100 }}
      gl={{ antialias: false, alpha: true, powerPreference: "high-performance" }}
      aria-hidden
    >
      <hemisphereLight args={["#f6f1e6", "#3b3a35", 0.9]} />
      <directionalLight position={[-5, 7, 6]} intensity={2.1} color="#fff0d4" castShadow
        shadow-mapSize={[1024, 1024]} shadow-bias={-0.0004} shadow-camera-left={-6} shadow-camera-right={6} shadow-camera-top={6} shadow-camera-bottom={-6} />
      <directionalLight position={[6, -2, 4]} intensity={0.5} color="#d7e3ff" />
      <Environment resolution={64} frames={1}>
        <Lightformer intensity={1.6} position={[0, 4, 6]} scale={[10, 3, 1]} color="#fff6e6" />
        <Lightformer intensity={0.8} position={[-6, 0, 2]} rotation-y={Math.PI / 2} scale={[6, 6, 1]} color="#e9e2d2" />
        <Lightformer intensity={0.6} position={[6, 1, -2]} rotation-y={-Math.PI / 2} scale={[6, 4, 1]} color="#D7EB79" />
      </Environment>
      <Rig />
      <Ready />
    </Canvas>
  );
}
