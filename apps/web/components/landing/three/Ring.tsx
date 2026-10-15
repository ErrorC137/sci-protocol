"use client";

import { forwardRef, useMemo } from "react";
import * as THREE from "three";
import { concreteMaterial, limeMaterial } from "./materials";

export const SEGMENTS = 6;
export const R_OUT = 1.5;
export const R_IN = 1.0;
const DEPTH = 0.42;
const GAP = 0.06; // radians between segments

function segmentGeometry(i: number) {
  const step = (Math.PI * 2) / SEGMENTS;
  // Clockwise from 12 o'clock, like the SVG twin: segment 0 sits just right of the top.
  const a1 = Math.PI / 2 - i * step - GAP / 2;
  const a0 = a1 - (step - GAP);
  const s = new THREE.Shape();
  s.absarc(0, 0, R_OUT, a0, a1, false);
  s.absarc(0, 0, R_IN, a1, a0, true);
  s.closePath();
  const g = new THREE.ExtrudeGeometry(s, { depth: DEPTH, bevelEnabled: true, bevelThickness: 0.035, bevelSize: 0.03, bevelSegments: 2, curveSegments: 40 });
  g.translate(0, 0, -DEPTH / 2);
  g.computeVertexNormals();
  return g;
}

export interface RingHandles {
  /** lime overlay materials, one per segment - animate opacity / emissiveIntensity */
  lime: THREE.MeshStandardMaterial[];
}

// The segmented "Circular O": a concrete shell per segment, plus a lime overlay mesh (slightly proud of the
// surface) that fades in and glows when the segment is lit.
export const Ring = forwardRef<THREE.Group, { handles: RingHandles }>(function Ring({ handles }, ref) {
  const { geos, concrete } = useMemo(() => ({
    geos: Array.from({ length: SEGMENTS }, (_, i) => segmentGeometry(i)),
    concrete: concreteMaterial("#e6e1d7", 0.9),
  }), []);
  useMemo(() => {
    handles.lime = geos.map(() => {
      const m = limeMaterial();
      m.transparent = true;
      m.opacity = 0;
      m.depthWrite = false;
      return m;
    });
  }, [geos, handles]);

  return (
    <group ref={ref}>
      {geos.map((g, i) => (
        <group key={i}>
          <mesh geometry={g} material={concrete} castShadow receiveShadow />
          <mesh geometry={g} material={handles.lime[i]} scale={1.004} renderOrder={2} />
        </group>
      ))}
    </group>
  );
});
