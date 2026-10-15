-- Small binary objects the API has to keep across restarts: local-IPFS objects (project metadata,
-- milestone evidence, vault ciphertext) and uploaded application forms. With Postgres configured these
-- live here instead of on the service's disk, so a host without a persistent disk (Render free) loses
-- nothing on restart. Applied on every API boot, like 0001; keep it idempotent.

create table if not exists blobs (
  namespace   text not null,             -- 'ipfs' | 'uploads'
  key         text not null,             -- CID or sha256
  data        bytea not null,
  created_at  timestamptz not null default now(),
  primary key (namespace, key)
);
