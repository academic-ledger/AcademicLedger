-- Migration 003 — author disavowals ("NOT ME").
-- A per-author exclusion list: works that OpenAlex's imperfect author clustering wrongly
-- attributed to this author (e.g. a different person with the same name). Server-side overlay
-- only — getAuthorRecord drops these from the author's view; nothing is written back to OpenAlex.
-- The member-facing "NOT ME" button (ORCID-gated) is backlogged; rows can be seeded manually now.
CREATE TABLE IF NOT EXISTS author_excluded_works (
  author_oaid TEXT NOT NULL,            -- OpenAlex Author ID disavowing the work
  work_oaid   TEXT NOT NULL,            -- the mis-attributed OpenAlex Work ID
  reason      TEXT,                     -- free-text (e.g. "different Karl T. Ulrich")
  source      TEXT DEFAULT 'manual',    -- 'manual' (admin) | 'member' (self-service, future)
  created_at  TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (author_oaid, work_oaid)
);
