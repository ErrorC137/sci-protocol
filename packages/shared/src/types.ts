// Mirrors apps/api/app/models/schemas.py. Keep in sync when the API shapes change.

export type FieldId =
  | "materials" | "agritech" | "biotech" | "energy" | "environmental"
  | "food_science" | "health" | "digital" | "manufacturing";

export type ApplicantType = "individual" | "university" | "startup" | "sme" | "consortium";

export interface ProjectProfile {
  nickname?: string | null;
  fields: FieldId[];
  subdomains: string[];
  trl: number;
  evidence: string[];
  applicant_type: ApplicantType;
  has_entity?: boolean | null;
  country: string;
  institution_type?: string | null;
  funding_min_usd: number;
  funding_max_usd: number;
  uses_of_funds: string[];
  months_to_milestone: number;
  constraints: string[];
}

export interface Applicant {
  name?: string | null;
  email?: string | null;
  phone?: string | null;
  organization?: string | null;
  position?: string | null;
  address?: string | null;
}

export interface Grant {
  id: string;
  funder_id: string | null;
  funder_name: string | null;
  funder_type: string | null;
  title: string;
  summary: string | null;
  source: string;
  source_ref: string;
  url: string | null;
  trl_min: number | null;
  trl_max: number | null;
  fields: string[];
  eligible_countries: string[];
  applicant_types: string[];
  requires_incorporation: boolean | null;
  ip_assignment_required: boolean | null;
  amount_min_usd: number | null;
  amount_max_usd: number | null;
  currency: string | null;
  equity_taken: boolean | null;
  deadline: string | null;
  rolling: boolean;
  cycle_note: string | null;
  application_mode: string | null;
  form_url: string | null;
  verified: boolean;
  confidence: "high" | "medium" | "low";
  notes: string | null;
  raw: { subdomains?: string[]; form_note?: string | null; amount_original?: { min?: number; max?: number; currency?: string } | null; [k: string]: unknown };
  updated_at: string;
}

export type RuleStatus = "pass" | "fail" | "unknown";
export interface RuleResult { rule: string; status: RuleStatus; detail: string }

export interface ScoreBreakdown {
  similarity: number;
  field_overlap: number;
  trl_centering: number;
  amount_fit: number;
  deadline_feasibility: number;
  total: number;
}

export interface Explanation { why_matched: string; strengthen: string; source: "llm" | "template" }

export interface MatchResult {
  grant: Grant;
  eligible: boolean;
  rules: RuleResult[];
  score: ScoreBreakdown | null;
  days_left: number | null;
  effort: { hours_low?: number; hours_high?: number; field_count?: number; basis?: string; prefill_available?: boolean };
  warnings: string[];
  explanation: Explanation | null;
}

export interface Unlock { change: string; label: string; count: number; examples: string[] }

export interface TRLAssessment {
  trl: number;
  name: string;
  plain: string;
  evidence_range: [number, number] | null;
  consistent: boolean | null;
  note: string;
}

export interface MatchResponse {
  matches: MatchResult[];
  excluded_count: number;
  excluded_by_rule: Record<string, number>;
  near_misses: MatchResult[];
  unlocks: Unlock[];
  trl_assessment: TRLAssessment;
  corpus_size: number;
  embedder: string;
}

export type FieldType =
  | "text" | "textarea" | "number" | "date" | "email" | "tel"
  | "checkbox" | "radio" | "select" | "signature";

export interface FieldSpec {
  id: string;
  label: string;
  type: FieldType;
  options: string[];
  maxlen: number | null;
  required: boolean;
  hint: string | null;
  page: number | null;
  narrative: boolean;
}

export interface FormTemplate {
  id: string;
  form_url: string;
  kind: "pdf_acroform" | "pdf_flat" | "html_form";
  title: string | null;
  fields: FieldSpec[];
  source_sha256: string;
  extraction: string;
  created_at: string;
}

export type FillStatus = "green" | "amber" | "red";
export type FieldValue = string | boolean | string[] | null;

export interface FilledField {
  field_id: string;
  label: string;
  type: FieldType;
  value: FieldValue;
  status: FillStatus;
  source: "profile" | "llm" | "template" | "user" | "none";
  rationale: string | null;
  narrative: boolean;
  required: boolean;
  options: string[];
  maxlen: number | null;
  warnings: string[];
  confirmed: boolean;
  acknowledged_blank: boolean;
}

export interface Application {
  id: string;
  grant_id: string;
  template_id: string;
  fields: FilledField[];
  reviewed: boolean;
  reviewed_at: string | null;
  llm_used: boolean;
  created_at: string;
}

export interface ReviewProblem { field_id: string | null; label: string; problem: string }

export interface ApplicationOut {
  application: Application;
  template: FormTemplate;
  summary: { green: number; amber: number; red: number; total: number };
  problems: ReviewProblem[];
}

export interface Taxonomy {
  fields: { id: FieldId; label: string; subdomains: string[] }[];
  trl: { level: number; name: string; plain: string }[];
  evidence: { id: string; label: string; trl_range: [number, number] }[];
  applicant_types: { id: ApplicantType; label: string }[];
  institution_types: { id: string; label: string }[];
  uses_of_funds: { id: string; label: string }[];
  constraints: { id: string; label: string }[];
  countries: { code: string; name: string; currency: string }[];
  funder_types: string[];
}

export interface Health {
  status: string;
  store: string;
  corpus_size: number;
  sources: Record<string, number>;
  embedder: string;
  llm: { enabled: boolean; model: string | null };
  ipfs: "pinata" | "local";
  chain: { chain_id: number; deployment: boolean };
  indexer: { next_block: number; events: number; error: string | null } | null;
}

export interface ChainEvent {
  contract: string;
  event: string;
  args: Record<string, unknown>;
  block: number;
  tx: string;
  log_index: number;
}

/** Non-confidential project metadata pinned to IPFS and referenced on-chain. */
export interface ProjectMetadata {
  schema: "sci-protocol/project-metadata@1";
  nickname: string;
  fields: string[];
  subdomains: string[];
  trl: number;
  evidence: string[];
  country: string;
  applicant_type: string;
  uses_of_funds: string[];
  disclosure: string;
}
