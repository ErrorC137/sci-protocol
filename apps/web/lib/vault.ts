import { concat, hexToBytes, keccak256, toBytes } from "viem";

/**
 * Client-side vault crypto. The AES-GCM key is derived (HKDF-SHA256) from a wallet signature over a fixed
 * message; ECDSA wallet signatures are deterministic (RFC 6979), so the same wallet re-derives the same key
 * later. Neither the key nor the plaintext ever leaves the browser - only ciphertext is pinned, and only
 * keccak256(ciphertext) goes on-chain.
 */
export const VAULT_MESSAGE =
  "SCI Protocol vault key v1\n\nSigning this message derives your encryption key inside this browser. " +
  "The key and your plaintext never leave this device. Signing costs no gas.";

const MAGIC = toBytes("SCIV1");
// WebCrypto wants ArrayBuffer-backed views; copy viem's ArrayBufferLike-typed bytes.
const ab = (u: Uint8Array): Uint8Array<ArrayBuffer> => new Uint8Array(u);
const SALT = ab(toBytes("sci-vault-v1"));

export async function deriveKey(signature: `0x${string}`): Promise<CryptoKey> {
  const base = await crypto.subtle.importKey("raw", ab(hexToBytes(signature)), "HKDF", false, ["deriveKey"]);
  return crypto.subtle.deriveKey(
    { name: "HKDF", hash: "SHA-256", salt: SALT, info: new Uint8Array() },
    base,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

export interface VaultPayload {
  text: string;
  file?: { name: string; type: string; b64: string };
  sealedAt: string;
}

export async function seal(key: CryptoKey, payload: VaultPayload): Promise<{ blob: Uint8Array; hash: `0x${string}` }> {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const plain = new TextEncoder().encode(JSON.stringify(payload));
  const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, plain));
  const blob = concat([MAGIC, iv, ct]);
  return { blob, hash: keccak256(blob) };
}

export async function open(key: CryptoKey, blob: Uint8Array): Promise<VaultPayload> {
  if (!MAGIC.every((b, i) => blob[i] === b)) throw new Error("Not a vault blob");
  const iv = ab(blob.slice(MAGIC.length, MAGIC.length + 12));
  const ct = ab(blob.slice(MAGIC.length + 12));
  const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, ct);
  return JSON.parse(new TextDecoder().decode(plain)) as VaultPayload;
}

export const hashBlob = (blob: Uint8Array) => keccak256(blob);

export async function fileToB64(f: File): Promise<string> {
  const buf = new Uint8Array(await f.arrayBuffer());
  let s = "";
  for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode(...buf.subarray(i, i + 0x8000));
  return btoa(s);
}
