-- Migration 002 — staged coverage rollout (QaL_spec.md §11 "Coverage rollout").
-- All additive / idempotent. Adds: a source tag on percentile tables (skeleton vs sampled),
-- a confidence tier on calibration models, and a resumable checkpoint table for the rollout.

-- Percentile tables can now be a cheap exact "skeleton" (count/group_by queries: n, p0, tail
-- ladder) or a "sampled" interior refinement. Refines write a newer snapshot, so the read's
-- `snapshot DESC` naturally supersedes a skeleton with the sampled CDF when present.
ALTER TABLE cohort_percentiles ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'sampled';

-- Calibration confidence tier (lowest -> highest):
--   parametric   : 2-param (citation half-life + tail) model, shrunk to a discipline prior;
--                  no direct maturation fit yet. (calibration-pending in the UI)
--   fitted       : direct (age, observed-pct) mapping with per-age split-conformal widening,
--                  but the leave-one-vintage-out back-test has not yet reached ~0.90 coverage
--                  (or there are too few matured vintages to test). (calibration-pending)
--   gate-passed  : fitted AND back-test coverage ~0.90. Only this tier shows a QaL forecast.
ALTER TABLE calibration_models ADD COLUMN IF NOT EXISTS confidence TEXT;

-- The existing seed (1803/1802/1800) is gate-passed and must never be silently downgraded.
UPDATE calibration_models SET confidence = 'gate-passed'
 WHERE confidence IS NULL AND community IN ('1803', '1802', '1800');

-- Resumable checkpoint for the rollout: one row per (step, subfield, vintage) unit of work.
-- The launchd resume reads this to skip finished units; the morning coverage report is a query.
-- Postgres forbids NULLs in PK columns, so not-applicable dimensions use sentinels:
-- subfield='' (whole-run steps like footprint) and vintage=0 (whole-subfield steps).
CREATE TABLE IF NOT EXISTS coverage_progress (
  step       TEXT NOT NULL,        -- 'footprint' | 'skeleton' | 'sample' | 'calibrate' | 'backtest'
  subfield   TEXT NOT NULL DEFAULT '',   -- subfield id ('' for the footprint step)
  vintage    INT  NOT NULL DEFAULT 0,    -- publication year (0 for whole-subfield steps)
  status     TEXT,                 -- 'done' | 'partial' | 'empty' | 'error'
  confidence TEXT,                 -- calibration tier reached, when applicable
  detail     JSONB,                -- free-form: n, p0, cost, back-test coverage, error msg, ...
  updated_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (step, subfield, vintage)
);
CREATE INDEX IF NOT EXISTS coverage_progress_step ON coverage_progress(step, status);
