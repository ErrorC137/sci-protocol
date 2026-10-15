"use client";

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef, type MutableRefObject } from "react";
import * as THREE from "three";
import { SECTION_IDS, store } from "../motion";
import { LIME, concreteMaterial, limeMaterial } from "./materials";
import { SEGMENTS } from "./Ring";

const damp = THREE.MathUtils.damp;
const STREAM = 110; // particles in the capital stream
const SPLIT_EVERY = 4; // from station 04, every 4th particle peels off to Pool B
const VESSEL = new THREE.Vector3(2.0, -1.1, 0.35);
const VESSEL_MOUTH = VESSEL.clone().setY(VESSEL.y + 0.45);

// S3 props, in ring-local units (ring radius 1.5), so they orbit with the ring:
//   01 battery cells · 02 lime capital stream along the lit arc · 03 fee coins · 04 part of the stream splits off
//   into the Innovation Treasury vessel (Pool B) · 05 cathode crystal at the centre. The loop close pulses all of it.
export function Stations({ phase }: { phase: MutableRefObject<number> }) {
  const cells = useRef<THREE.Group>(null);
  const coins = useRef<THREE.Group>(null);
  const vessel = useRef<THREE.Group>(null);
  const vesselFill = useRef<THREE.Mesh>(null);
  const crystal = useRef<THREE.Mesh>(null);
  const stream = useRef<THREE.Points>(null);

  const mats = useMemo(() => {
    const cellBody = new THREE.MeshStandardMaterial({ color: "#2a2f2c", roughness: 0.5, metalness: 0.4 });
    const copper = new THREE.MeshStandardMaterial({ color: "#B57856", roughness: 0.3, metalness: 0.9 });
    const glass = new THREE.MeshStandardMaterial({ color: "#e8efe0", roughness: 0.1, metalness: 0, transparent: true, opacity: 0.22, depthWrite: false });
    const fill = limeMaterial(); fill.emissiveIntensity = 0.5;
    const gem = limeMaterial(); gem.emissiveIntensity = 0.6; gem.roughness = 0.15;
    return { cellBody, copper, glass, fill, gem, base: concreteMaterial("#bdb7ab", 0.5) };
  }, []);

  const seeds = useMemo(() => Float32Array.from({ length: STREAM }, (_, i) => (i * 0.61803398875) % 1), []);
  const positions = useMemo(() => new Float32Array(STREAM * 3), []);
  const p0 = useMemo(() => new THREE.Vector3(), []), c = useMemo(() => new THREE.Vector3(), []), out = useMemo(() => new THREE.Vector3(), []);

  useFrame((state, dt) => {
    dt = Math.min(dt, 1 / 20);
    const t = state.clock.elapsedTime;
    const inFlow = SECTION_IDS[Math.min(SECTION_IDS.length - 1, Math.floor(store.t))] === "flow";
    const ph = inFlow ? phase.current : -1;
    const closed = ph === SEGMENTS - 1;
    const show = (g: THREE.Object3D | null, on: boolean, lambda = 5) => {
      if (!g) return;
      const s = damp(g.scale.x, on ? 1 : 0, lambda, dt);
      g.scale.setScalar(s);
      g.visible = s > 0.01;
    };

    show(cells.current, ph >= 0 && ph <= 1);
    show(coins.current, ph >= 2 && ph <= 3);
    show(vessel.current, ph >= 3);
    show(crystal.current, ph >= 4);
    if (coins.current) coins.current.rotation.y = t * 0.6;
    if (crystal.current) {
      crystal.current.rotation.y = t * 0.7;
      crystal.current.rotation.x = Math.sin(t * 0.5) * 0.3;
      (crystal.current.material as THREE.MeshStandardMaterial).emissiveIntensity = closed ? 1.0 + Math.sin(t * 3) * 0.25 : 0.6;
    }
    if (vesselFill.current) {
      const target = ph >= 3 ? (closed ? 0.95 : 0.55) : 0.05;
      const k = damp(vesselFill.current.scale.y, target, 1.5, dt);
      vesselFill.current.scale.y = k;
      vesselFill.current.position.y = -0.42 + 0.42 * k;
    }

    // Capital stream: particles run clockwise along the lit arc; from station 04 a share peels off to Pool B.
    const pts = stream.current;
    if (!pts) return;
    const streamOn = ph >= 1;
    pts.visible = damp((pts.material as THREE.PointsMaterial).opacity, streamOn ? 1 : 0, 4, dt) > 0.02;
    (pts.material as THREE.PointsMaterial).opacity = damp((pts.material as THREE.PointsMaterial).opacity, streamOn ? 1 : 0, 4, dt);
    const span = (Math.max(1, ph + 1) / SEGMENTS) * Math.PI * 2;
    for (let i = 0; i < STREAM; i++) {
      const u = (seeds[i] + t * 0.12) % 1;
      if (ph >= 3 && i % SPLIT_EVERY === 0) {
        // quadratic bezier from the ring's right side down into the vessel mouth
        p0.set(Math.cos(-0.35) * 1.25, Math.sin(-0.35) * 1.25, 0.32);
        c.set(2.1, -0.1, 0.55);
        out.copy(p0).multiplyScalar((1 - u) * (1 - u)).addScaledVector(c, 2 * (1 - u) * u).addScaledVector(VESSEL_MOUTH, u * u);
      } else {
        const a = Math.PI / 2 - u * span;
        const r = 1.25 + Math.sin(i * 12.9898) * 0.12;
        out.set(Math.cos(a) * r, Math.sin(a) * r, 0.3 + Math.sin(i * 4.1 + t) * 0.04);
      }
      positions[i * 3] = out.x; positions[i * 3 + 1] = out.y; positions[i * 3 + 2] = out.z;
    }
    (pts.geometry.attributes.position as THREE.BufferAttribute).needsUpdate = true;
  });

  return (
    <group>
      {/* 01 · Commercial assets: battery cells / black-mass blocks under the ring */}
      <group ref={cells} scale={0} position={[0, -2.05, 0.4]}>
        {Array.from({ length: 7 }, (_, i) => (
          <group key={i} position={[(i - 3) * 0.32, 0, (i % 2) * 0.12]}>
            <mesh material={mats.cellBody} castShadow><cylinderGeometry args={[0.1, 0.1, 0.36, 20]} /></mesh>
            <mesh material={mats.copper} position={[0, 0.2, 0]}><cylinderGeometry args={[0.045, 0.045, 0.05, 12]} /></mesh>
          </group>
        ))}
        <mesh material={mats.base} position={[0, -0.22, 0]} receiveShadow><boxGeometry args={[2.4, 0.08, 0.5]} /></mesh>
      </group>

      {/* 03 · Platform revenue: a small stack of fee coins */}
      <group ref={coins} scale={0} position={[1.5, 1.5, 0.35]}>
        {Array.from({ length: 4 }, (_, i) => (
          <mesh key={i} material={i === 3 ? mats.fill : mats.copper} position={[0, i * 0.06, 0]}><cylinderGeometry args={[0.2, 0.2, 0.05, 28]} /></mesh>
        ))}
      </group>

      {/* 04 · Innovation Treasury vessel (Pool B) */}
      <group ref={vessel} scale={0} position={VESSEL}>
        <mesh material={mats.glass}><cylinderGeometry args={[0.32, 0.32, 0.9, 32, 1, true]} /></mesh>
        <mesh ref={vesselFill} material={mats.fill} scale={[0.92, 0.05, 0.92]} position={[0, -0.42, 0]}><cylinderGeometry args={[0.3, 0.3, 0.84, 32]} /></mesh>
        <mesh material={mats.base} position={[0, -0.5, 0]}><cylinderGeometry args={[0.38, 0.38, 0.08, 32]} /></mesh>
      </group>

      {/* 05 · Research development: cathode crystal at the centre of the ring */}
      <mesh ref={crystal} scale={0} material={mats.gem}><octahedronGeometry args={[0.42, 0]} /></mesh>

      {/* 02 · The capital stream */}
      <points ref={stream} frustumCulled={false}>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]} /></bufferGeometry>
        <pointsMaterial size={0.055} color={LIME} transparent opacity={0} depthWrite={false} toneMapped={false} sizeAttenuation />
      </points>
    </group>
  );
}
