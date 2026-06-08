-- academic Ledger / QaL  — Level 0 datastore (Postgres)
-- The web app reads these tables; the batch pipeline writes them.

-- Raw work records pulled from OpenAlex (the universal layer source).
CREATE TABLE IF NOT EXISTS works (
  oaid            TEXT PRIMARY KEY,           -- OpenAlex Work ID, e.g. W4385447813 (canonical key)
  doi             TEXT,
  title           TEXT,
  publication_year INT,
  primary_subfield TEXT,                      -- OpenAlex subfield id, e.g. '1803'
  primary_field    TEXT,
  cited_by_count   INT,
  counts_by_year   JSONB,                     -- {"2019": 4, "2020": 11, ...} for the early-signal/age model
  is_oa            BOOLEAN,
  is_retracted     BOOLEAN DEFAULT FALSE,
  raw              JSONB,                      -- full OpenAlex record for reproducibility
  fetched_at       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS works_subfield_year ON works(primary_subfield, publication_year);

-- Per (subfield, year) citation->percentile table. Makes observed percentile an O(1) lookup.
-- Store the empirical CDF as breakpoints; interpolate at read time.
CREATE TABLE IF NOT EXISTS cohort_percentiles (
  subfield        TEXT,
  publication_year INT,
  n               INT,                         -- cohort size
  cdf             JSONB,                        -- [{"cites":0,"pct":31.2}, {"cites":1,"pct":48.0}, ...]
  snapshot        TEXT,                         -- e.g. 'openalex-2026-05'
  PRIMARY KEY (subfield, publication_year, snapshot)
);

-- Calibrated Layer-B model per community: maps (observed pct, age) -> posterior over eventual pct.
-- Stored as a lookup grid; the API reads median/interval/bucket masses from it.
CREATE TABLE IF NOT EXISTS calibration_models (
  community       TEXT,                         -- subfield id or community key
  age_years       INT,
  obs_pct_bin     INT,                          -- lower edge of observed-percentile bin
  eventual_median NUMERIC,
  ci_lo           NUMERIC,
  ci_hi           NUMERIC,
  p_ge50 NUMERIC, p_ge75 NUMERIC, p_ge90 NUMERIC, p_ge95 NUMERIC, p_ge99 NUMERIC,
  n_train         INT,                          -- support behind this cell
  model_version   TEXT,
  PRIMARY KEY (community, age_years, obs_pct_bin, model_version)
);

-- Final served QaL record per work (read-through cache; refreshed monthly).
CREATE TABLE IF NOT EXISTS qal_records (
  oaid            TEXT PRIMARY KEY REFERENCES works(oaid),
  reference_class JSONB,                         -- {field, field_label, vintage_year, n}
  obs_percentile  NUMERIC,                       -- universal layer, always present
  calibrated      BOOLEAN,                       -- false => calibration-pending
  qal_point       NUMERIC,                       -- null if not calibrated
  qal_ci_lo       NUMERIC,
  qal_ci_hi       NUMERIC,
  class_prob      JSONB,                          -- {ge50,ge75,ge90,ge95,ge99}
  method_version  TEXT,
  data_snapshot   TEXT,
  computed_at     TIMESTAMPTZ DEFAULT now()
);

-- Author entities (for the author page).
CREATE TABLE IF NOT EXISTS authors (
  oaid        TEXT PRIMARY KEY,                  -- OpenAlex Author ID
  orcid       TEXT,
  display_name TEXT,
  affiliation TEXT,
  works_count INT,
  cited_by_count INT,
  fetched_at  TIMESTAMPTZ DEFAULT now()
);
