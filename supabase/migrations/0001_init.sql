-- SCI Protocol core schema (brief §3.2). Apply in the Supabase SQL editor or `supabase db push`.
-- The API also applies this file itself on startup when DATABASE_URL is set (idempotent).

create extension if not exists vector;

create table if not exists funders (
  id       uuid primary key,
  name     text not null,
  type     text,             -- government | accelerator | incubator | foundation | corporate | web3 | crowdfunding | multilateral
  country  text,
  website  text
);

create table if not exists grants (
  id                      uuid primary key,
  funder_id               uuid references funders(id),
  title                   text not null,
  summary                 text,
  source                  text not null,      -- grants_gov | eu_sedia | curated | ...
  source_ref              text not null,      -- original id at source
  url                     text,
  -- eligibility (the fields matching runs on)
  trl_min                 int,
  trl_max                 int,
  fields                  text[] not null default '{}',
  eligible_countries      text[] not null default '{}',   -- ISO2; '{*}' = global; '{}' = unknown
  applicant_types         text[] not null default '{}',   -- individual | university | startup | sme | consortium
  requires_incorporation  boolean,
  ip_assignment_required  boolean,
  -- money & time
  amount_min_usd          numeric,
  amount_max_usd          numeric,
  currency                text,
  equity_taken            boolean,
  deadline                timestamptz,
  rolling                 boolean not null default false,
  cycle_note              text,
  -- application mechanics
  application_mode        text,               -- pdf_form | web_form | email | portal
  form_url                text,
  -- provenance
  verified                boolean not null default false,
  confidence              text not null default 'medium',
  notes                   text,
  -- matching
  embedding               vector(1024),
  embedding_model         text,
  raw                     jsonb not null default '{}',
  updated_at              timestamptz not null default now(),
  unique (source, source_ref)
);

create index if not exists grants_embedding_hnsw on grants using hnsw (embedding vector_cosine_ops);
create index if not exists grants_deadline_idx on grants (deadline);
create index if not exists grants_fields_gin on grants using gin (fields);
create index if not exists grants_countries_gin on grants using gin (eligible_countries);

-- Non-confidential profiles only (controlled vocabulary). Never method, composition or data.
create table if not exists projects (
  id          uuid primary key,
  profile     jsonb not null,
  created_at  timestamptz not null default now()
);

create table if not exists matches (
  project_id  uuid references projects(id) on delete cascade,
  grant_id    uuid references grants(id) on delete cascade,
  score       numeric,
  detail      jsonb,
  created_at  timestamptz not null default now(),
  primary key (project_id, grant_id)
);

-- Field extraction is the expensive step: cached once per form, not per application.
create table if not exists form_templates (
  id             uuid primary key,
  form_url       text not null unique,
  kind           text not null,              -- pdf_acroform | pdf_flat | html_form
  title          text,
  fields         jsonb not null,
  field_count    int not null,
  source_sha256  text not null,
  extraction     text not null,
  created_at     timestamptz not null default now()
);

create table if not exists applications (
  id           uuid primary key,
  grant_id     uuid references grants(id) on delete cascade,
  template_id  uuid references form_templates(id),
  fields       jsonb not null,
  reviewed     boolean not null default false,
  reviewed_at  timestamptz,
  llm_used     boolean not null default false,
  created_at   timestamptz not null default now()
);
