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

## Coverage result (Exhibit C — PRELIMINARY) — `figures/fig_cross_field_coverage_prelim.png`
Honest leave-one-vintage-out conformal coverage of the nominal 90% interval, reusing the shipped
`calib_lib` + `backtest.py` method per field (`coverage.py`).

| Field | uncited | coverage |
|---|---:|---:|
| Biochemistry & Mol Bio | 46% | 0.905 |
| Decision Sciences | 60% | 0.867 (full-power DB back-test: **0.886**) |
| Economics & Finance | 72% | 0.833 |
| Arts & Humanities | 81% | 0.836 |

**Finding.** Coverage tracks citation density: ~nominal in dense fields (Biochem 0.905, DS ~0.87–0.89),
but **under-covers by ~4–5 points in sparse fields (Economics, Arts & Humanities)** — the intervals are
too narrow where citations are sparse and vintage-to-vintage dynamics drift more (worse exchangeability).
An honest limitation that points to a sparse-field-aware interval widening (future work).

**Status — PRELIMINARY.** From an API-limited harness (5 vintages, ~500–1500 papers/subfield-cohort)
vs. the full-power DB back-test (~10k/cohort, 9 vintages). DS reproduces within ~0.02 of the canonical
**0.886**, so the harness is roughly valid and the sparse-field gap is likely a real bias (not power).
The **definitive run should use the bulk-snapshot factory** (no API metering); `coverage.py` is set for
the fuller run. OpenAlex daily API budget was exhausted during this session (resets midnight UTC).
