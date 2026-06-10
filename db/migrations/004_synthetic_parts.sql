-- Migration 004 — store the synthetic field's per-subfield PARTS, so the served QaL can be
-- computed by the blend-weighted calibration (apply each constituent subfield's calibration to
-- the focal's percentile in that subfield, blend by weight) rather than a single-label swap.
-- parts = [{"sid": "1803", "weight": 0.34, "pct": 99.1}, ...] for the used (>=2% weight) cohorts.
ALTER TABLE synthetic_field ADD COLUMN IF NOT EXISTS parts JSONB;
