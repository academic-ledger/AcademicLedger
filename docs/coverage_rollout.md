# Stage-one coverage rollout (OID department)

Implements QaL_spec §11, *Coverage rollout via staged sampling*. Goal: broad, **honestly-labeled**
coverage of the OID department's subfields, improved incrementally — not perfection on night one.
The job (`pipeline/coverage_rollout.py`) is **resumable** and **budget-aware**: it runs as far as
the day's OpenAlex budget allows, checkpoints every unit, exits cleanly on a budget-429, and the
daily launchd fire (`pipeline/run_coverage.sh`) resumes the next day.

## Steps (budget order: cheap → expensive)

1. **Footprint** — resolve the 30 OID standing faculty to OpenAlex authors (Penn-preferred,
   topic-disambiguated; each match carries a `confidence` flag and low-confidence ones are listed
   for review). Tally each author's subfields from their OpenAlex `topics` (one request/author,
   equal department weight per faculty) → a ranked subfield table with a cumulative-coverage curve
   and the 90%/95% marks → `data/oid_footprint.json`. Names the target set and its priority.
2. **Skeleton percentile tables** — per target (subfield × vintage), an *exact coarse* CDF from one
   `group_by=cited_by_count` histogram (the populous head) plus a few `cited_by_count:>X` tail
   counts. Covers the whole head immediately at ~4 requests/cohort; `cohort_percentiles.source =
   'skeleton'`.
3. **Refine + hybrid calibration** — per cohort, a **uniform random** 1k sample fills the interior
   CDF (`source = 'sampled'`, written under a higher-sorting snapshot so it supersedes the
   skeleton). Per subfield, calibration is **hybrid**:
   - the proven **nonparametric** fit (`calib_lib`: tail-dense local-linear + per-age split-conformal)
     where ≥3 matured vintages each have ≥50 sampled works, then the leave-one-vintage-out
     back-test → `fitted`, or `gate-passed` when LOVO coverage ≈ 0.90;
   - the **parametric** fallback (`calib_parametric`: citation half-life + tail, shrunk to a
     discipline prior, §7) otherwise → `parametric`.

## Confidence tiers (`calibration_models.confidence`, surfaced on every served record)

`parametric` < `fitted` < `gate-passed`. **Only `gate-passed` is shown as a forecast** (`compute_qal`
gates `calibrated` on it); lower tiers stay calibration-pending and the UI names the tier. The seed
(1803/1802/1800) is already `gate-passed` and is **excluded** from Steps 2/3 — never downgraded.

## Conventions / hygiene

Uniform random sampling only; full-population denominator including the uncited atom at mid-rank
`100·p₀/2`; the same convention for r_obs and r∞. Idempotent upserts under a single per-month
snapshot label. `coverage_progress` is the checkpoint + the morning report (a query).

## Deferred refinements (backlog)

- **Recency-weighted, works-level footprint.** Step 1 currently uses OpenAlex's per-author `topics`
  aggregation (cheap, recency-ish) rather than pulling each author's works and applying the
  synthetic-field recency weighting. The works-level pass is a deeper, quota-heavier refinement.
- **Research-grade parametric model.** The half-life+tail fallback is deliberately simple (rank
  persistence + maturity-scaled truncated-normal interval). A principled two-parameter eventual-rank
  model is future work; it only affects the `parametric` tier, which is never shown as a forecast.
- **group_by tail completeness.** For very large cohorts the top-200 `group_by` buckets miss some
  sparse high-citation values; the tail ladder pins the upper percentiles, but the skeleton is
  coarse there by construction (sampled interiors supersede it).
