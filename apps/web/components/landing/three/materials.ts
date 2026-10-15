import * as THREE from "three";

// Procedural concrete: multi-octave value noise painted into a canvas once, used as colour, roughness and bump.
// No image files, no network.
function valueNoise(size: number, seed: number) {
  const rand = (x: number, y: number) => {
    const s = Math.sin(x * 127.1 + y * 311.7 + seed * 74.7) * 43758.5453;
    return s - Math.floor(s);
  };
  const smooth = (t: number) => t * t * (3 - 2 * t);
  const sample = (x: number, y: number, cell: number) => {
    const gx = Math.floor(x / cell), gy = Math.floor(y / cell);
    const fx = smooth(x / cell - gx), fy = smooth(y / cell - gy);
    const n = size / cell; // wrap so the texture tiles
    const v = (i: number, j: number) => rand(((gx + i) % n + n) % n, ((gy + j) % n + n) % n);
    return THREE.MathUtils.lerp(THREE.MathUtils.lerp(v(0, 0), v(1, 0), fx), THREE.MathUtils.lerp(v(0, 1), v(1, 1), fx), fy);
  };
  const out = new Float32Array(size * size);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      let a = 0, w = 0.5, sum = 0;
      for (const cell of [64, 32, 16, 8, 4]) { a += sample(x, y, cell) * w; sum += w; w *= 0.55; }
      out[y * size + x] = a / sum;
    }
  }
  return out;
}

let cache: { map: THREE.CanvasTexture; rough: THREE.CanvasTexture } | null = null;

function concreteTextures() {
  if (cache) return cache;
  const size = 256;
  const n = valueNoise(size, 3.1), pits = valueNoise(size, 9.7);
  const mk = (fn: (v: number, p: number) => number) => {
    const c = document.createElement("canvas");
    c.width = c.height = size;
    const ctx = c.getContext("2d")!;
    const img = ctx.createImageData(size, size);
    for (let i = 0; i < size * size; i++) {
      const v = Math.max(0, Math.min(255, fn(n[i], pits[i])));
      img.data[i * 4] = img.data[i * 4 + 1] = img.data[i * 4 + 2] = v;
      img.data[i * 4 + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = 4;
    return t;
  };
  const map = mk((v, p) => 205 + (v - 0.5) * 55 - (p > 0.74 ? (p - 0.74) * 220 : 0));
  map.colorSpace = THREE.SRGBColorSpace;
  const rough = mk((v) => 200 + (v - 0.5) * 80);
  cache = { map, rough };
  return cache;
}

export function concreteMaterial(tint = "#c9c3b7", repeat = 1) {
  const { map, rough } = concreteTextures();
  const m = new THREE.MeshStandardMaterial({
    color: tint, map: map.clone(), roughnessMap: rough.clone(), bumpMap: rough.clone(), bumpScale: 0.6,
    roughness: 1, metalness: 0,
  });
  [m.map, m.roughnessMap, m.bumpMap].forEach((t) => { if (t) { t.repeat.set(repeat, repeat); t.needsUpdate = true; } });
  return m;
}

export const LIME = new THREE.Color("#D7EB79");

// Signal Lime that can glow: emissive above 1 with tone mapping off, so only these meshes pass the bloom
// threshold (selective bloom without a second render pass).
export function limeMaterial() {
  return new THREE.MeshStandardMaterial({
    color: LIME, emissive: LIME, emissiveIntensity: 0, roughness: 0.45, metalness: 0.1, toneMapped: false,
  });
}
