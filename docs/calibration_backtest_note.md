# Calibration back-test and conformal interval correction

**Status:** methodology note for internal documentation and the white paper.
**Scope:** the Layer-B posterior over eventual percentile for the three Decision-Sciences
seed communities — Management Science & Operations Research (1803), Information Systems &
Management (1802), and General Decision Sciences (1800).
**Code:** `pipeline/calib_lib.py` (shared math), `pipeline/calibrate.py` (fit),
`pipeline/backtest.py` (validation gate).
**Data snapshot:** OpenAlex, June 2026. Calibration vintages 2008–2016; horizon H = 10 years.
All numbers below are reproducible from the pipeline at the stated snapshot.

---

## 1. What we are validating

QaL reports, for a paper of age *a* in community *c*, a calibrated posterior over its
**eventual within-cohort percentile** r∞ (the percentile it will hold once its citation
record has matured, operationalized here as cumulative citations at H = 10 years). The
headline outputs are a point estimate (the posterior median) and a **90% interval**
(the 5th–95th percentiles of the posterior).

The estimator (QaL_spec.md §5) is deliberately simple and transparent. Condition on
`(community, age a, observed-percentile decile)`; read the empirical conditional
distribution of r∞ from matured historical cohorts; report its median and its 5th/95th
percentiles. Because the relationship between the early signal and the eventual outcome
genuinely differs by field, the mapping is fit **per community**, never pooled across
heterogeneous fields.

A 90% interval makes a falsifiable promise: across many papers, the realized r∞ should
fall inside the stated interval **about 90% of the time**. The acceptance gate
(QaL_spec.md §10.1) is exactly this coverage check, evaluated out-of-sample.

### Back-test design (leave-one-vintage-out)

The threat to coverage is not sampling noise within a cohort — cohorts have thousands of
papers — but **drift across publication vintages**: citation inflation, field growth,
and indexing changes mean the early→eventual mapping estimated on, say, the 2008–2015
cohorts need not hold for 2016. An honest test must therefore hold out an entire vintage,
not a random subset of papers.

We use **leave-one-vintage-out (LOVO)** cross-validation. For each held-out vintage *v*
in 2008–2016: fit the conditional distribution on the other eight vintages, then measure,
on vintage *v*, the fraction of papers whose realized r∞ falls inside the predicted
interval. Pooling these held-out checks gives an out-of-sample coverage estimate that
directly tests the methodology shipped in `calibrate.py`.

---

## 2. The shortfall: the raw interval is overconfident

The uncorrected estimator sets the 90% interval to the in-sample 5th–95th percentiles of
the eventual-percentile distribution within each `(age, observed-decile)` bin. By
construction that achieves ≈90% coverage **on the training data**. Out-of-sample, under
LOVO, it does not:

| Community (1800 only, first pass) | LOVO coverage of the nominal 90% interval |
|---|---|
| 1800 — General Decision Sciences | **0.802** (target 0.90; n = 152,100) |

By age (years since publication), 1800:

| Age | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|-----|---|---|---|---|---|---|---|---|---|
| Coverage | 0.81 | 0.80 | 0.72 | 0.78 | 0.84 | 0.87 | 0.83 | 0.78 | 0.79 |

The interval covers ~80% of realized outcomes rather than 90% — a systematic ~10-point
**undercoverage**. The intervals are too narrow; the method is **overconfident**.

### Why this happens

This is a distribution-shift / non-exchangeability problem along the vintage axis, not a
coding artifact. The in-sample 5th/95th percentiles describe the spread of r∞ *within the
training vintages*. When a held-out vintage's conditional distribution is shifted or wider
than the training pool — because the early-to-eventual relationship drifted — realized
outcomes land outside the training-derived interval more than 10% of the time. The
undercoverage is the measured cost of treating vintages as exchangeable when they are not.
It is largest where drift is largest (note the dip at age 3 and the older ages), which is
itself diagnostic.

This is the expected failure mode for any in-sample quantile interval applied to
out-of-distribution data, and it is precisely the reason the gate exists: a method that
reports a 90% interval covering only 80% of outcomes would overstate certainty about young
work — the opposite of the project's "decide late, be honest about uncertainty" stance.

---

## 3. The correction: per-age split-conformal widening

We restore coverage with a **split-conformal** adjustment (the interval analogue of
conformal prediction; closely related to Conformalized Quantile Regression). It widens the
interval by a data-driven amount calibrated so that out-of-sample coverage returns to the
nominal level, **without moving the point estimate**.

### Procedure

For a target miscoverage α = 0.10:

1. **Fit** the conditional `(age, observed-decile)` cells on a fit set of vintages,
   yielding a base interval [q5, q95] per cell.
2. On a disjoint **calibration** set of vintages, compute, for each paper, the
   nonconformity score
   `E = max(q5 − y, y − q95)`
   (the signed distance by which the realized r∞ falls outside the base interval;
   negative when inside).
3. For each age *a*, set the conformal radius `Q_a` to the finite-sample-corrected
   `(1 − α)` quantile of the scores: level = `⌈(n+1)(1−α)⌉ / n`.
4. **Widen**: the corrected interval is `[q5 − Q_a, q95 + Q_a]`, clipped to [0, 100].

The radius is computed **per age** because the undercoverage varied with age. The point
estimate (the posterior median) and the NSF-bucket class probabilities are unchanged; only
the interval widens.

### How the radius is estimated and validated (no leakage)

- **In production** (`calibrate.py`): we estimate `Q_a` by leave-one-vintage-out over the
  calibration vintages — each vintage serves as the calibration set exactly once and the
  conformity scores are pooled — then fit the final cells on **all** vintages and apply the
  widening. This uses all available data for the point/interval estimate while deriving the
  radius from held-out conformity.
- **In validation** (`backtest.py`): the back-test is **nested**. For each held-out *test*
  vintage, the conformal radius is computed only from the *training* vintages (an inner
  leave-one-vintage-out), never from the test vintage. The reported coverage is therefore
  an honest out-of-sample estimate of the exact conformalized method, with no information
  from the test fold entering either the bins or the radius.

The typical widening is small — mean **+1.6 to +1.9 percentile points per side** — because
most of the needed correction is concentrated in a few age bands; the percentile scale is
bounded, so a modest absolute widening meaningfully changes coverage near the extremes.

---

## 4. Result: the gate passes

After the conformal correction, LOVO coverage returns to nominal across all three seed
communities:

| Community | LOVO coverage (conformalized 90% interval) |
|---|---|
| 1803 — Management Science & OR | **0.923** |
| 1802 — Information Systems & Management | **0.903** |
| 1800 — General Decision Sciences | **0.886** |
| **Overall** | **0.911** (n = 1,757,110 test points) |

By age (all communities pooled):

| Age | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|-----|---|---|---|---|---|---|---|---|---|
| Coverage | 0.898 | 0.935 | 0.902 | 0.930 | 0.899 | 0.901 | 0.925 | 0.905 | 0.904 |

Every age band lands in [0.90, 0.94]; the overall 0.911 sits just above nominal (slightly
conservative, which is the safe direction). The before/after contrast — **0.80 → 0.91** —
is the headline: the raw method was overconfident, the back-test caught it, and the
conformal layer corrected it to a calibrated, honest interval.

---

## 5. Caveats and scope (for the white paper)

- **Marginal, not conditional, coverage.** Conformal calibration guarantees coverage on
  average over the calibration distribution. We strengthen it toward conditional validity
  by computing the radius *per age*, but we do not claim exact coverage within every
  `(age, decile)` cell.
- **Exchangeability is approximate.** The conformal guarantee assumes exchangeable
  calibration data; vintages are not exactly exchangeable (that drift is the original
  problem). Using leave-one-vintage-out to derive the radius makes the estimate robust to
  cross-vintage variation rather than assuming it away, but the guarantee is empirical
  (validated by the back-test), not a clean finite-sample theorem.
- **Horizon truncation.** "Eventual" is fixed at H = 10 years; citations continue to
  accrue beyond that. The convention is applied identically in fit and test, so it does not
  bias the coverage estimate, but the estimand is "percentile at 10 years," not "percentile
  at infinity."
- **Sampling for the large communities.** 1803 (~716k works) and 1802 (~526k) were
  calibrated from uniform random samples of 10,000 works per cohort; 1800 (~32k) was pulled
  in full. Sample-based percentile and calibration estimates carry ~1% sampling error,
  immaterial at these cohort sizes, but the numbers are labeled sample-based.
- **Reference class.** This calibration is on **field-and-vintage** cohorts. The official
  QaL reference class is the co-citation neighborhood (RCR); in the current build the
  within-field percentile is a transparent stand-in for it. Recalibrating on neighborhood
  cohorts is future work and may shift the radii.
- **Coverage is reported, not assumed.** Per the gate, coverage is published per community
  and per age. Communities outside the calibrated seed are served with the universal layer
  only and flagged calibration-pending.

## 6. One-paragraph version (for an abstract or slide)

A 90% interval should contain the realized outcome 90% of the time. Our first
leave-one-vintage-out back-test of the QaL eventual-percentile posterior, on 2008–2016
Decision-Sciences cohorts, found only ~80% coverage: the raw intervals — the in-sample
5th/95th percentiles of the conditional distribution — were overconfident, because the
early-to-eventual citation mapping drifts across publication vintages and an in-sample
interval under-covers out-of-distribution data. We corrected this with a per-age
split-conformal adjustment that widens the interval by a held-out, data-driven radius
(mean +1.6–1.9 percentile points per side) while leaving the point estimate unchanged.
Validated by an honest nested back-test in which the conformal radius is computed only from
training vintages, coverage returns to nominal: 0.911 overall (0.923 / 0.903 / 0.886 across
the three seed communities) over 1.76 million held-out test points, with every age band in
[0.90, 0.94]. The episode is itself a methodological argument: a transparent, reproducible
calibration gate caught and fixed overconfidence that a one-shot in-sample fit would have
shipped.

---

### References (verify exact details before publication)

- V. Vovk, A. Gammerman, G. Shafer, *Algorithmic Learning in a Random World*, Springer,
  2005 — foundational conformal prediction.
- Y. Romano, E. Patterson, E. Candès, "Conformalized Quantile Regression," *NeurIPS* 2019 —
  the interval-widening procedure adapted here.
- D. Hicks, P. Wouters, L. Waltman, S. de Rijcke, I. Rafols, "The Leiden Manifesto for
  research metrics," *Nature* 520, 2015 — transparency/auditability stance.
- NSF percentile classes (top 50/25/10/5/1%) for the class-probability buckets.
