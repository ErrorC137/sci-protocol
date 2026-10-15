import type {
  Applicant, ApplicationOut, ChainEvent, Explanation, FieldValue, FormTemplate, Grant, Health, MatchResponse,
  ProjectProfile, Taxonomy, TRLAssessment,
} from "@sci/shared";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, public body: any) {
    super(typeof body?.detail === "string" ? body.detail : `API error ${status}`);
  }
}

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(API_URL + path, {
    ...init,
    headers: init?.body instanceof FormData || init?.body instanceof Blob
      ? init?.headers
      : { "content-type": "application/json", ...(init?.headers || {}) },
  });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw new ApiError(r.status, body);
  return body as T;
}

export interface GrantFilters {
  q?: string;
  field?: string[];
  country?: string;
  applicant_type?: string;
  trl?: number;
  funder_type?: string;
  no_equity?: boolean;
  include_closed?: boolean;
  limit?: number;
  offset?: number;
}

export const api = {
  health: () => j<Health>("/health"),
  taxonomy: () => j<Taxonomy>("/meta/taxonomy"),
  trlCheck: (trl: number, evidence: string[]) =>
    j<TRLAssessment>("/meta/trl-check", { method: "POST", body: JSON.stringify({ trl, evidence }) }),
  grants: (f: GrantFilters) => {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries(f)) {
      if (v === undefined || v === "" || v === false) continue;
      if (Array.isArray(v)) v.forEach((x) => p.append(k, x));
      else p.set(k, String(v));
    }
    return j<{ items: { grant: Grant; similarity: number }[]; total: number }>(`/grants?${p}`);
  },
  grant: (id: string) => j<Grant>(`/grants/${id}`),
  match: (profile: ProjectProfile) => j<MatchResponse>("/match", { method: "POST", body: JSON.stringify({ profile }) }),
  explain: (profile: ProjectProfile, grant_ids: string[]) =>
    j<{ explanations: Record<string, Explanation>; llm: boolean }>("/match/explain", {
      method: "POST", body: JSON.stringify({ profile, grant_ids }),
    }),
  grantForm: (grantId: string) => j<FormTemplate>(`/grants/${grantId}/form`),
  uploadForm: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return j<FormTemplate>("/forms/upload", { method: "POST", body: fd });
  },
  createApplication: (body: { grant_id: string; template_id?: string; profile: ProjectProfile; applicant: Applicant }) =>
    j<ApplicationOut>("/applications", { method: "POST", body: JSON.stringify(body) }),
  application: (id: string) => j<ApplicationOut>(`/applications/${id}`),
  editApplication: (id: string, edits: { field_id: string; value?: FieldValue; confirmed?: boolean; acknowledged_blank?: boolean }[]) =>
    j<ApplicationOut>(`/applications/${id}`, { method: "PATCH", body: JSON.stringify({ edits }) }),
  review: (id: string, attest: boolean) =>
    j<ApplicationOut>(`/applications/${id}/review`, { method: "POST", body: JSON.stringify({ attest }) }),
  exportUrl: (id: string, format: "pdf" | "md" | "json") => `${API_URL}/applications/${id}/export?format=${format}`,
  pinJson: (obj: object) => j<{ cid: string; pinned: string; gateway_url: string }>("/ipfs/pin-json", {
    method: "POST", body: JSON.stringify(obj),
  }),
  pinBytes: (bytes: Uint8Array) =>
    j<{ cid: string; pinned: string; gateway_url: string }>("/ipfs/pin", {
      method: "POST", body: new Blob([bytes as BlobPart]), headers: { "content-type": "application/octet-stream" },
    }),
  ipfsUrl: (cid: string) => `${API_URL}/ipfs/${cid}`,
  ipfsJson: async <T,>(cid: string): Promise<T | null> => {
    try {
      const r = await fetch(`${API_URL}/ipfs/${cid}`);
      return r.ok ? ((await r.json()) as T) : null;
    } catch {
      return null;
    }
  },
  activity: (projectId: number) => j<{ events: ChainEvent[] }>(`/chain/activity?project_id=${projectId}&limit=200`),
};
