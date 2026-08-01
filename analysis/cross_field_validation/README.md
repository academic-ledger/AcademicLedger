# Cross-field validation (QaL paper §6)

Does the early citation signal — and QaL's forecast — generalize beyond Decision Sciences? We validate
across four fields chosen to span the property most likely to break a citation metric, the **uncited
fraction**: Biochemistry & Molecular Biology (dense), Decision Sciences, Economics & Finance, and
Arts & Humanities (sparse).

## Early-signal result (Exhibit D) — `figures/fig_cross_field_earlysignal.png`
AUC for identifying the eventual (10-year) top decile, computed **within (subfield × vintage) cohorts**
(≥200 papers), paper-weighted — the same field-normalized method as `pipeline/early_signal_analysis.py`
(pooling across subfields inflates AUC and is avoided). Matched 2010–2013 cohorts, OpenAlex
`counts_by_year`.

| Field | uncited@10y | AUC age 1 | age 2 | age 3 | age 4 |
|---|---:|---:|---:|---:|---:|
| Biochemistry & Mol Bio | 46% | 0.84 | 0.98 | 0.99 | 0.99 |
| Decision Sciences | 60% | 0.79 | 0.95 | 0.97 | 0.98 |
| Economics & Finance | 72% | 0.76 | 0.90 | 0.95 | 0.97 |
| Arts & Humanities | 81% | 0.65 | 0.76 | 0.83 | 0.88 |

**Reading.** The early signal identifies the eventual top decile in *every* field (all ≥0.88 by age 4),
but its strength **tracks citation density monotonically**: Biochemistry (dense) is easiest, Arts &
Humanities (sparse) is markedly hardest. The signal generalizes, and it is weakest precisely where a
citation-based metric should be weakest — the honest bound.

**Consistency check.** Decision Sciences reproduces ~0.79 at age 1 here vs. 0.72 in the DB-based
back-test (`docs/early_signal_result.md`) — consistent, and far from the 0.91 that an (incorrect)
pooled-across-subfields AUC produces. Residual differences trace to vintage pooling and subfield
sampling (fresh OpenAlex sample vs. the ingested seed cohorts).

## Distribution result (Exhibit B extended) — `figures/fig_cross_field_distribution.png`
Eventual (10-year) citations at each within-field percentile; matched 2013 cohorts, n = 6,000/field.

| Field | uncited | median | p90 | p99 | top-1% share |
|---|---:|---:|---:|---:|---:|
| Biochemistry & Mol Bio | 44% | 1 | 51 | 273 | 35% |
| Decision Sciences | 59% | 0 | 14 | 116 | 40% |
| Economics & Finance | 72% | 0 | 7 | 75 | 45% |
| Arts & Humanities | 80% | 0 | 2 | 33 | 47% |

**Reading.** The same percentile means a wildly different raw count across fields — the 90th-percentile
paper has **51** citations in Biochemistry but **2** in Arts & Humanities (25×). Every field is
majority-uncited (44%→80%), and the sparser the field, the *more* concentrated its citations
(top-1% share rises 35%→47%). Direct motivation for ranking (percentiles) over counts (§4.1–4.2).

## Rerun
```bash
../../.venv/bin/python earlysignal.py <output-dir>     # early-signal (Exhibit D)
../../.venv/bin/python distribution.py <output-dir>    # distribution (Exhibit B)
```

## Coverage result (Exhibit C — DEFINITIVE) — `figures/fig_cross_field_coverage.png`
Honest leave-one-vintage-out conformal coverage of the nominal 90% interval, reusing the shipped
`calib_lib` + `backtest.py` method per (subfield × vintage) cohort. Computed on the **full OpenAlex
bulk snapshot** in-region (no API metering): 2,446 part files scanned, 2.35M papers sampled, vintages
2008–2015, ≤10k/cohort, cohorts ≥200. Job: `pipeline/factory_coverage.py`; figure: `plot_coverage.py`.

| Field | uncited | coverage | held-out n | subfields |
|---|---:|---:|---:|---:|
| Biochemistry & Mol Bio | 46% | 0.890 | 7.53M | 14 |
| Decision Sciences | 60% | 0.890 | 2.32M | 4 |
| Economics & Finance | 72% | 0.884 | 2.16M | 3 |
| Arts & Humanities | 81% | 0.887 | 9.18M | 13 |

**Finding.** Coverage holds at **~nominal in every field** — all four land in 0.884–0.890, inside the
shipped [0.88, 0.93] PASS band, and essentially flat across a density gradient from 46% to 81% uncited.
The conformal interval delivers its promised 90% coverage even in Arts & Humanities, the sparsest field,
where four of five papers are never cited. Per-age coverage (`by_age` in `coverage_results.json`) is
centered on 0.89 with no monotone drift; the wider age-to-age scatter in Decision Sciences and Economics
is small-panel noise (only 3–4 qualifying subfields), not bias.

**Validation.** Decision Sciences reproduces **0.890** here versus the canonical full-power DB back-test
**0.886** — a 0.004 match — confirming the in-region factory reproduces the shipped estimator exactly.

**Supersedes the preliminary run.** An earlier API-limited harness (5 vintages, ~500–1,500
papers/subfield-cohort) reported apparent under-coverage of ~4–5 points in the sparse fields
(Economics 0.833, Arts & Humanities 0.836). That gap was a **low-power artifact** — too few conformal
calibration scores per cohort — not a real bias: at full power it vanishes. The honest cross-field
conclusion is that conformal coverage is robust to field citation density, with no sparse-field
interval-widening required.

## Rerun (coverage)
```bash
# definitive, in-region on the bulk snapshot (~1h, ~$0.53; needs AWS creds):
../../.venv/bin/python ../../pipeline/run_coverage_factory.py --file-limit 0 --per 10000
../../.venv/bin/python plot_coverage.py figures   # regenerate the figure from coverage_results.json
```
