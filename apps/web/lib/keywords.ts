import type { Grant } from "@sci/shared";

/**
 * Local-only similarity for the researcher's private keywords. Runs entirely in the browser:
 * the keywords are never sent to the API, the LLM, or anyone else.
 */
const stem = (w: string) => w.toLowerCase().replace(/[^a-z0-9฀-๿]+/g, "").replace(/(ies|es|s)$/, "");

export function keywordBoost(keywords: string[], g: Grant): number {
  const kws = keywords.map((k) => k.trim()).filter(Boolean);
  if (!kws.length) return 0;
  const text = [g.title, g.summary, ...(g.raw.subdomains || []), ...g.fields].join(" ").toLowerCase();
  const words = new Set(text.split(/[^a-z0-9฀-๿]+/).map(stem));
  let hits = 0;
  for (const kw of kws) {
    const parts = kw.split(/\s+/).map(stem).filter(Boolean);
    if (parts.length && parts.every((p) => words.has(p))) hits += 1;
  }
  return hits / kws.length;
}

/** Weight of the local boost added on top of the server's hybrid score (which never saw the keywords). */
export const KEYWORD_WEIGHT = 0.05;
