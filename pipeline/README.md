# pipeline — batch jobs (run on GitHub Actions, NOT on Vercel)

Order: `pull_cohort.py` -> `build_percentiles.py` -> `calibrate.py` -> `compute_qal.py`.
Writes to Postgres when `DATABASE_URL` is set; without it, `pull_cohort.py` dumps JSONL to `data/`
so you can develop the modeling offline.

Env: `DATABASE_URL` (Neon), `OPENALEX_MAILTO` (polite pool). See ../.env.example.
Config: `cohorts.yml` defines the calibrated seed communities and the score/calibration vintages.
