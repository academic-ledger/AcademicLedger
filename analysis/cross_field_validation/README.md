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

## Still to do (per field)
- Calibration / coverage back-test (Exhibit C) — needs Layer-B conformal calibration per field.
- Distribution / percentile-transform panels (Exhibit B extended).
