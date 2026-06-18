-- On-demand synthetic-field serving cache (any oaid; NO foreign key to works, unlike
-- synthetic_field). Filled only by the client-triggered /api/synthetic/:oaid endpoint — the
-- behavior gate that keeps flat crawler GETs from triggering the ~15-40-call synthetic compute —
-- and read on the paper-page server GET (zero OpenAlex). The app also creates this lazily
-- (CREATE TABLE IF NOT EXISTS) on first write, so this migration is a record, not a prerequisite.
create table if not exists synthetic_cache (
  oaid        text primary key,
  payload     jsonb not null,          -- synthetic display overrides (reference_class, obs, qal, composition)
  computed_at timestamptz not null default now()
);
