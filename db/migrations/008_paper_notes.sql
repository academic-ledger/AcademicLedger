-- Community layer v0 — C2 (canonical version + author notes). The first ACADEMIC-LEDGER-ORIGINATED,
-- authenticated-write data: an attributed overlay merged onto the paper page at render. One-to-many
-- (an author may add several items per paper: a canonical-version link + related references + notes).
-- User-data side only — NEVER writes the metric tables (works, cohort_percentiles, calibration_models,
-- qal_records, synthetic_field) and never changes QaL. Also lazy-created by the app on first write.
create table if not exists paper_notes (
  id           serial primary key,
  user_id      integer not null references users(id) on delete cascade,
  work_oaid    text not null,                 -- the paper this note is ON
  target_oaid  text,                          -- the referenced paper (e.g. the canonical version); null = plain note
  target_title text,                          -- denormalized title of the target, for the link text
  relation     text not null default 'note',  -- 'canonical' | 'supersedes' | 'related' | 'note'
  body         text,                          -- plain-text comment (escaped at render; no HTML)
  visible      boolean not null default true,
  status       text not null default 'active',-- 'active' | 'deleted'
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index if not exists paper_notes_work on paper_notes (work_oaid) where visible and status = 'active';
