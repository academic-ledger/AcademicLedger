-- Migration 005 — view-triggered synthetic-field backfill.
-- The paper page enqueues an oaid here when it has no cached synthetic_field blend; the worker
-- pipeline/synth_worker.py drains the queue on the FREE polite pool, computes the blend, and
-- persists it to synthetic_field. The next view (and Explore) then serve the real synthetic field
-- from cache instead of the single-field stand-in. Keeps heavy compute off the request path
-- (Vercel does no heavy compute) and off the metered budget.
CREATE TABLE IF NOT EXISTS synth_view_queue (
  oaid         text PRIMARY KEY,
  requested_at timestamptz NOT NULL DEFAULT now(),
  attempts     int  NOT NULL DEFAULT 0,   -- bumped on each failed compute; worker skips past a cap
  last_error   text
);
-- pending lookups: oldest-first among rows still under the attempt cap
CREATE INDEX IF NOT EXISTS synth_view_queue_pending ON synth_view_queue (requested_at) WHERE attempts < 5;
