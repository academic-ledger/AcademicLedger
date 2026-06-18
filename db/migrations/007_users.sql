-- Community layer v0 — C1 (ORCID sign-in). The user-data side of the attributed overlay, kept
-- SEPARATE from the metric/data tables (works, cohort_percentiles, calibration_models, qal_records,
-- synthetic_field), which this slice never writes. No password column — identity is ORCID OAuth only.
-- The web app also creates these lazily (CREATE TABLE IF NOT EXISTS) on first login, so this
-- migration is the source of record, not a hard prerequisite.

-- One row per signed-in researcher, keyed by their ORCID iD.
create table if not exists users (
  id            serial primary key,
  orcid_id      text unique not null,        -- e.g. 0000-0002-1825-0097
  display_name  text,
  created_at    timestamptz not null default now(),
  last_login_at timestamptz not null default now()
);

-- Cache of the member's PUBLIC ORCID works (pulled from the ORCID API at login), for C2/C3 to
-- confirm authorship. DOIs + ORCID put-codes; OpenAlex Work IDs are resolved from the DOI later.
create table if not exists orcid_works (
  user_id    integer not null references users(id) on delete cascade,
  put_code   text not null,                  -- ORCID's per-work identifier
  doi        text,
  title      text,
  fetched_at timestamptz not null default now(),
  primary key (user_id, put_code)
);
