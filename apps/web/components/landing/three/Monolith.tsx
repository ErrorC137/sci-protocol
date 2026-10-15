"use client";

import { useFrame } from "@react-three/fiber";
import { forwardRef, useMemo, useRef } from "react";
import * as THREE from "three";
import { concreteMaterial, limeMaterial } from "./materials";
import { R_OUT } from "./Ring";

// Hero set piece (brand board mood): a concrete monolith with a circular opening the ring sits in, a second
// slab behind it, raw ore / black-mass rocks and copper nuggets at the base, a few lime shards, drifting dust.
// Everything is procedural geometry - no GLB, no HDRI.

const W = 3.7, H = 4.6, BASE = -2.55; // slab size; BASE = bottom edge, in ring units (ring centre = origin)

function slabWithHole() {
  const s = new THREE.Shape();
  s.moveTo(-W / 2, BASE); s.lineTo(W / 2, BASE); s.lineTo(W / 2, BASE + H); s.lineTo(-W / 2, BASE + H); s.closePath();
  const hole = new THREE.Path();
  hole.absarc(0, 0, R_OUT + 0.08, 0, Math.PI * 2, true);
  s.holes.push(hole);
  const g = new THREE.ExtrudeGeometry(s, { depth: 1.1, bevelEnabled: true, bevelThickness: 0.04, bevelSize: 0.04, bevelSegments: 1, curveSegments: 64 });
  g.translate(0, 0, -0.85);
  return g;
}

// Deterministic pseudo-random so the composition is identical on every load.
function rng(seed: number) {
  let s = seed;
  return () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
}

function rockGeometry(r: number, seed: number) {
  const g = new THREE.IcosahedronGeometry(r, 1);
  const rand = rng(seed);
  const pos = g.attributes.position as THREE.BufferAttribute;
  const v = new THREE.Vector3();
  const seen = new Map<string, number>(); // keep shared vertices together so faces stay closed
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    const key = `${v.x.toFixed(3)},${v.y.toFixed(3)},${v.z.toFixed(3)}`;
    const k = seen.get(key) ?? 0.72 + rand() * 0.5;
    seen.set(key, k);
    v.multiplyScalar(k);
    v.y *= 0.72; // squat
    pos.setXYZ(i, v.x, v.y, v.z);
  }
  g.computeVertexNormals();
  return g;
}

const ROCKS: { x: number; z: number; r: number; kind: "mass" | "copper" | "lime"; rot: number }[] = [
  { x: -1.75, z: 0.55, r: 0.48, kind: "mass", rot: 0.4 }, { x: -1.05, z: 0.95, r: 0.32, kind: "mass", rot: 1.2 },
  { x: -0.45, z: 0.85, r: 0.17, kind: "copper", rot: 0.2 }, { x: 0.15, z: 1.05, r: 0.24, kind: "mass", rot: 2.1 },
  { x: 0.75, z: 0.75, r: 0.38, kind: "mass", rot: 0.9 }, { x: 1.3, z: 1.1, r: 0.15, kind: "copper", rot: 1.7 },
  { x: 1.8, z: 0.5, r: 0.52, kind: "mass", rot: 2.6 }, { x: 1.0, z: 1.3, r: 0.1, kind: "lime", rot: 0.6 },
  { x: -1.4, z: 1.25, r: 0.13, kind: "copper", rot: 2.9 }, { x: -0.75, z: 1.35, r: 0.09, kind: "lime", rot: 1.1 },
  { x: 2.25, z: 1.0, r: 0.24, kind: "mass", rot: 0.3 }, { x: -2.25, z: 0.95, r: 0.26, kind: "mass", rot: 1.9 },
];

function Dust({ count = 220 }: { count?: number }) {
  const ref = useRef<THREE.Points>(null);
  const { positions, seeds } = useMemo(() => {
    const rand = rng(42);
    const positions = new Float32Array(count * 3), seeds = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (rand() - 0.5) * 8;
      positions[i * 3 + 1] = BASE + rand() * 6;
      positions[i * 3 + 2] = (rand() - 0.2) * 3;
      seeds[i] = rand() * 100;
    }
    return { positions, seeds };
  }, [count]);
  useFrame((_, dt) => {
    const p = ref.current?.geometry.attributes.position as THREE.BufferAttribute | undefined;
    if (!p) return;
    const t = performance.now() / 1000;
    for (let i = 0; i < count; i++) {
      let y = p.getY(i) + dt * (0.05 + (seeds[i] % 1) * 0.06);
      if (y > BASE + 6) y = BASE;
      p.setY(i, y);
      p.setX(i, p.getX(i) + Math.sin(t * 0.3 + seeds[i]) * dt * 0.03);
    }
    p.needsUpdate = true;
  });
  return (
    <points ref={ref}>
      <bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]} /></bufferGeometry>
      <pointsMaterial size={0.028} color="#8f897d" transparent opacity={0.75} depthWrite={false} sizeAttenuation />
    </points>
  );
}

export const Monolith = forwardRef<THREE.Group>(function Monolith(_, ref) {
  const { slab, back, concrete, concreteDark, mass, copper, lime, rocks } = useMemo(() => {
    const backG = new THREE.BoxGeometry(2.6, 5.6, 0.9);
    return {
      slab: slabWithHole(),
      back: backG,
      concrete: concreteMaterial("#ece8df", 1.4),
      concreteDark: concreteMaterial("#c2bdb2", 1.1),
      mass: new THREE.MeshStandardMaterial({ color: "#3a3d3a", roughness: 0.88, metalness: 0.12, flatShading: true }),
      copper: new THREE.MeshStandardMaterial({ color: "#B57856", roughness: 0.32, metalness: 0.85, flatShading: true }),
      lime: (() => { const m = limeMaterial(); m.emissiveIntensity = 1.25; return m; })(),
      rocks: ROCKS.map((r, i) => rockGeometry(r.r, 11 + i * 7)),
    };
  }, []);

  return (
    <group ref={ref}>
      <mesh geometry={slab} material={concrete} castShadow receiveShadow />
      <mesh geometry={back} material={concreteDark} position={[-1.55, 0.35, -1.6]} castShadow receiveShadow />
      {ROCKS.map((r, i) => (
        <mesh key={i} geometry={rocks[i]} material={r.kind === "mass" ? mass : r.kind === "copper" ? copper : lime}
          position={[r.x, BASE + r.r * 0.45, r.z]} rotation={[r.rot, r.rot * 1.7, r.rot * 0.6]} castShadow />
      ))}
      <Dust />
    </group>
  );
});
