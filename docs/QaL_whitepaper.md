# How QaL Works

### A quality estimate for scholarly papers, built from the open record

*Draft white paper prepared by Claude Opus 4.8 from project notes and code base. Written to nail down the data science; clean enough to post on academic-ledger.org. The seed-community calibration results below are real and back-tested (OpenAlex, June 2026 snapshot); values shown in worked single-paper examples are illustrative.*

---

## 1. What QaL is, and what problem it solves

Academic publishing bundles two functions that need not travel together: **distribution** (making work available) and **certification** (judging how good it is). Distribution is effectively solved. Certification is not: the journal system renders a slow, expensive, and noisy binary verdict, years after the fact, and compresses a continuous question into accept-or-reject.

QaL (said "qual") replaces that verdict with a measurement. For a paper *p*, QaL estimates where *p* will **eventually stand among its peers**, expressed as a percentile, and reports that estimate honestly with its uncertainty. It is computed from the open scholarly record, so it has no cold start and is reproducible by anyone.

This document specifies the estimand, the two-layer estimator, the conformal interval correction that makes the uncertainty honest, how the calibration generalizes across fields, the validation results, and the design choices that make the metric hard to game. It assumes the reader is comfortable with percentiles and elementary probability.

## 2. The estimand

Fix a long horizon *H* (here ten years after publication). For paper *p* define its **eventual percentile** *r∞(p)*: the rank, in [0,100], of *p*'s cumulative citations at age *H*, within *p*'s reference class and vintage (Section 3). The horizon makes "eventual" concrete; *r∞* is the target we are trying to predict before *H* has elapsed.

QaL is not a point claim about *r∞*. Because most of *r∞* is realized after the moment of evaluation, QaL is a **calibrated belief** about *r∞* given the evidence available so far. It reports three things, always against a stated reference class:

- a point estimate, the posterior median of *r∞*;
- a 90% interval, the 5th and 95th percentiles of the posterior;
- class probabilities, *P(r∞ ≥ c)* for the cut points *c* ∈ {50, 75, 90, 95, 99} of the NSF/Leiden percentile classes.

The honesty of the metric lives in the interval: a young paper earns a wide one, an established paper a narrow one. "Decide late" is not a rule imposed on top of the metric; it is what the interval does on its own.

## 3. Reference class

Every QaL is relative to an explicit reference class. The official one is a **synthetic field**: a vintage-matched blend of (topic, year) cohorts whose mixture weights describe the focal paper's intellectual community, with the percentile taken over the blended full population (Section 4). A blend rather than a single subject category is used because single-field labels misclassify interdisciplinary work badly, and field-normalization is the central difficulty in citation indicators (Waltman, 2016); the gold-standard version of this idea is algorithmic citation-network field delineation (Waltman & van Eck, 2012), which OpenAlex topics approximate. **Vintage** is the publication year. The official number is fixed so the reference class cannot be shopped; other classes are offered only for exploration.

The mixture weights are obtained in stages. At and shortly after posting, when there are no citations, they come from the focal paper's own references, weighted toward the **research front**: recent, specific references count more than old canonical ones, because the recent work locates the paper's live field while the canon only places it in a broad tradition. This is the long-standing distinction between a research front and an intellectual base (Persson, 1994); bibliographic coupling, the sharing of recent references, recovers the front most accurately (Boyack & Klavans, 2010), and the recency of references is itself a classical front measure (the Price Index; de Solla Price, 1970). As citing papers accumulate, the weights migrate to the co-citation community, the RCR-style view of how the field situates the paper (Hutchins et al., 2016), which is harder to game. The neighborhood is never the cohort we rank against (it is a popularity-biased, cited-only sample, Section 4); it only sets the weights.

In the current build the calibration is fit on field-and-vintage cohorts (OpenAlex subfield × year) as a transparent stand-in for the full synthetic-field blend; the back-tested numbers in Section 6 are on that stand-in, and recalibrating on the blend is future work.

## 4. Observed standing (Layer A)

The first layer is a fact, not a forecast. Within a paper's (reference class, vintage) cohort, compute its **observed percentile** *r_obs*: the empirical-CDF rank of its cumulative citations to date. With *n* the cohort size and *k* the number with strictly more citations, *r_obs = 100 · (1 − k/n)*. The large mass of uncited papers gets a single shared rank rather than an artificial spread.

This layer is exact, cheap (two count queries), and available for **any** indexed paper regardless of calibration. Percentiles, rather than raw counts, are the right currency because rescaled citation distributions are approximately universal across fields once normalized (Radicchi, Fortunato, & Castellano, 2008), and the question is always relative standing, not absolute volume.

### The uncited mass and the denominator

Roughly half of every cohort has zero citations, so how the uncited are handled decides what a percentile means. In the seed, Management Science & Operations Research is 53.6% uncited even at maturity (2015 cohort) and about 60% uncited at age two; General Decision Sciences runs 36% and 56%. This is not a tail, it is half the distribution.

The denominator is the **full population, cited and uncited**, never the cited papers alone. Ranking only among the cited would be a different quantity: with half the cohort uncited, the median cited paper sits near the 75th population percentile, so a cited-only percentile silently inflates every paper by the size of the uncited mass and, worse, puts the neighborhood headline on a different denominator from the field percentile, breaking the robustness-panel comparison. We rank against the whole cohort.

This is tractable, but it takes care, because the co-citation neighborhood is a **popularity-biased, cited-only sample**: a paper is co-cited with the focal in rough proportion to its own citation count, so the neighborhood over-represents highly-cited papers and by construction contains none of the uncited. We therefore do not rank the focal paper against its neighbors, which would compare it to an elite rather than to its community. We use the neighborhood only for what it estimates with low bias, the **topic mixture** of the focal paper's community (which topics, with what weights), and compute the percentile against the representative full population of that mixture: the blend of the full (topic, vintage) cohorts at the focal paper's vintage. Those cohorts already contain the uncited papers, so the uncited atom and its mass *p₀* emerge from the blend rather than being grafted on, and the misclassification robustness is preserved because the weights reflect the true intellectual community rather than a single OpenAlex label.

Concretely, the synthetic percentile is the **weight-average of the paper's percentile in each component subfield**: for citation count *c*, *r_obs = Σ_t w_t · pct_t(c)*, where *pct_t(c)* is its standing (same tie convention, full population including uncited) against subfield *t*'s vintage-matched distribution. This is exact, not an approximation: the CDF of a mixture is the weighted average of its components' CDFs, so ranking *c* in the pooled blend and weighting its per-subfield percentiles give the identical number, and each subfield's uncited mass is carried in its own *pct_t* so *p₀ = Σ_t w_t · p₀(t)* falls out. Each *pct_t(c)* is an O(1) lookup in the per-(subfield, vintage) percentile table, so the synthetic percentile is a handful of lookups and a weighted sum.

The uncited are tied, so they share one percentile. We assign the **mid-rank**, 100 · *p₀*/2 (about the 27th percentile for mature MS&OR, the 30th at age two), so a zero-citation paper reads as mid-low and indistinguishable from its uncited peers, not as rock bottom; the fractional assignment of Waltman & Schreiber (2013) is the field-standard refinement for handling this large tie mass cleanly. A focal paper that is itself uncited has no co-citation neighborhood of its own; it falls back to the universal field-and-vintage percentile (within the atom), and its neighborhood headline is marked calibration-pending rather than fabricated.

One consequence is worth stating plainly: across the bottom half of any young cohort the observed percentile has almost no resolution, because those papers are tied at the atom. That is the true information content of early citations for young work, and it is exactly why the calibrated forecast and its interval carry the weight. A paper uncited at age two has an eventual-percentile posterior that runs from the atom upward, because a sizeable share of today's uncited papers are cited later, and Layer B learns that lift. The same full-population denominator is used when the eventual percentile *r∞* is computed for calibration, so the uncited atom is present identically in the fit, in the conformal radius, and in the back-tested coverage of Section 6.

## 5. Calibration: from observed standing to eventual percentile (Layer B)

The second layer turns current standing into a calibrated forecast of eventual standing. Rather than projecting citation counts forward and re-ranking, we condition directly: for a paper of age *a* in community *c*, observed at percentile *r_obs*, we read the empirical conditional distribution

> *r∞ | (community c, age a, observed percentile)*,

estimated from **matured historical cohorts** (publication vintages 2008–2016, observed to the horizon *H* = 10 years). Age enters as a conditioning variable, so the partial-maturity of a young paper is handled by the data rather than by an explicit accrual rescaling. The conditioning on observed percentile is **high-resolution in the upper tail** (finer than deciles, or continuous via quantile regression), because the citation distribution is heaviest there: a coarse top-decile bin would collapse everything from the 90th to the 99.99th percentile into one cell and pull a clearly canonical paper toward that cell's median. The posterior is that empirical conditional distribution; from it we read the median (point), the 5th and 95th percentiles (the raw interval, corrected in Section 6), and the mass above each cut point (class probabilities). Because the early-to-eventual relationship genuinely differs by field, the mapping is fit **per community**, never pooled across heterogeneous fields.

Two properties follow without being imposed. Young papers carry wide posteriors and old papers tight ones: as age approaches the horizon the mapping converges to identity, so a mature paper at the 99.97th percentile forecasts about 99 to 100 with a tight interval rather than a regressed-down point. This is the decide-late behavior, derived from data. And the spread at each age is anchored to measured early-signal validity: in our operations cohort the rank correlation between early and eventual standing is roughly 0.5 at one year and rises toward 1 with age. That limited early predictability is consistent with the broader finding that long-term citation prediction is hard (the predictive claims of mechanistic models such as Wang, Song, & Barabási (2013) have themselves been contested), which is the reason to decide late. Correctness signals (retraction, expressions of concern) enter as an asymmetric penalty that floors or withdraws the posterior.

## 6. The conformal interval correction

A 90% interval makes a falsifiable promise: across many papers, the realized *r∞* should fall inside the stated interval about 90% of the time. We treat that coverage check as the primary acceptance gate, and we test it honestly. This section reports the first such back-test on the three Decision-Sciences seed communities, Management Science & Operations Research (1803), Information Systems & Management (1802), and General Decision Sciences (1800).

**Back-test design: leave-one-vintage-out.** The threat to coverage is not sampling noise within a cohort, since cohorts have thousands of papers, but **drift across publication vintages**: citation inflation, field growth, and indexing changes mean a mapping estimated on the 2008–2015 cohorts need not hold for 2016. An honest test therefore holds out an entire vintage, not a random subset of papers. For each held-out vintage *v* in 2008–2016 we fit the conditional distribution on the other eight vintages, then measure on *v* the fraction of papers whose realized *r∞* falls inside the predicted interval, and pool these out-of-sample checks.

**The shortfall.** The uncorrected estimator sets the 90% interval to the in-sample 5th–95th percentiles of *r∞* within each (age, observed-percentile) bin. By construction that achieves about 90% coverage on the training data. Out-of-sample it does not: for 1800 the pooled leave-one-vintage-out coverage was **0.802** against a 0.90 target (n = 152,100), with the by-age coverage ranging from 0.72 to 0.87. The intervals were systematically about ten points too narrow. This is the expected failure mode of any in-sample quantile interval applied to out-of-distribution data: the in-sample 5th/95th percentiles describe the spread within the training vintages, and when a held-out vintage's conditional distribution is shifted or wider, realized outcomes land outside the training-derived interval more than 10% of the time. The undercoverage is the measured cost of treating vintages as exchangeable when they are not, and it is largest where drift is largest.

**The correction: per-age split-conformal widening.** We restore coverage with a split-conformal adjustment, the interval analogue of conformal prediction and closely related to Conformalized Quantile Regression (Vovk, Gammerman, & Shafer, 2005; Romano, Patterson, & Candès, 2019; Angelopoulos & Bates, 2021). It widens the interval by a data-driven amount calibrated so that out-of-sample coverage returns to nominal, **without moving the point estimate**. For target miscoverage α = 0.10: fit the (age, observed-percentile) cells on a fit set of vintages, giving a base interval [q5, q95] per cell; on a disjoint calibration set, compute for each paper the nonconformity score *E = max(q5 − y, y − q95)* (the signed distance by which the realized *r∞* falls outside the base interval); for each age *a* set the conformal radius *Q_a* to the finite-sample-corrected (1 − α) quantile of those scores; and widen the interval to [q5 − Q_a, q95 + Q_a], clipped to [0, 100]. The radius is computed per age because the undercoverage varied with age. The typical widening is small, a mean of about **+1.6 to +1.9 percentile points per side**, because most of the needed correction is concentrated in a few age bands and the bounded percentile scale makes a modest absolute widening matter near the extremes.

**No leakage.** In production the radius is estimated by leave-one-vintage-out over the calibration vintages, then the final cells are fit on all vintages and the widening applied. In validation the back-test is **nested**: for each held-out test vintage the conformal radius is computed only from the training vintages, so neither the bins nor the radius see the test fold.

**Result: the gate passes.** After the correction, pooled leave-one-vintage-out coverage of the nominal 90% interval is:

| Community | Out-of-sample coverage |
|---|---|
| 1803 — Management Science & OR | 0.923 |
| 1802 — Information Systems & Management | 0.903 |
| 1800 — General Decision Sciences | 0.886 |
| **Overall** | **0.911** (n = 1,757,110 held-out test points) |

Every age band from one to nine years lands in [0.90, 0.94], and the overall 0.911 sits just above nominal, which is the safe direction. The before-and-after contrast, 0.80 to 0.91, is the headline: the raw method was overconfident, the back-test caught it, and the conformal layer corrected it to a calibrated, honest interval. The episode is itself a methodological argument for the transparent, reproducible gate: a one-shot in-sample fit would have shipped the overconfidence.

## 7. Generalizing across fields: a two-parameter family

Calibrating each subfield from a full cohort pull is feasible but unnecessary, and it does not scale to all of OpenAlex. The between-field variation in the mapping is concentrated in a low-dimensional summary: it varies **a great deal in timescale** and **little in rescaled shape**. The timescale is the citation-aging speed (the cited half-life): fast fields resolve early and their intervals narrow quickly; slow fields stay uncertain for years. The shape, once age is expressed in units of the field's own half-life, is approximately common, the calibration analogue of the distributional universality of Radicchi, Fortunato, & Castellano (2008) and of the lognormal regularity of cumulative citations (Stringer, Sales-Pardo, & Amaral, 2010; Wang, Song, & Barabási, 2013). This motivates modeling the calibration as a parametric family indexed by roughly two interpretable parameters per field: a timescale (half-life), governing how fast the interval narrows, and a dispersion/tail parameter, governing tail heaviness and residual spread.

Both are cheap to estimate, from a few hundred papers per subfield or from aggregate counts, far less than a full calibration. Consequences: **universe coverage** by instantiating a calibration for every subfield from its two parameters, with **hierarchical shrinkage** of sparse communities toward a discipline-level prior; **cheap onboarding** of any field; and a **validation gate, not a free lunch**. The family must be checked against directly-fitted calibrations in a handful of anchor subfields spanning fast and slow dynamics, confirming the mappings coincide after rescaling age by half-life; if a residual remains, add a third parameter (the asymptotic correlation) and re-test. Anchor, confirm the collapse, then extrapolate. The conformal radii of Section 6 are themselves field-specific and would be re-estimated per field under this scheme.

## 8. Validation and acceptance

QaL ships for a field only when it passes:

1. **Calibration / coverage.** On held-out mature cohorts (leave-one-vintage-out), the 90% interval covers realized *r∞* about 90% of the time, across ages and fields. **Status: passed for the three seed communities at 0.911 overall** (Section 6).
2. **Concordance at maturity.** For old papers, QaL agrees with established field-normalized indicators (RCR, mean-normalized citation scores, percentile classes), since at maturity *r_obs ≈ r∞*.
3. **Manipulation robustness.** Simulated self-citation and citation-cartel attacks move QaL negligibly; usage/attention inflation does not move the level at all.
4. **Reproducibility.** Every estimate recomputes from its published inputs, calibration cells, conformal radii, and data snapshot.
5. **Coverage honesty.** Coverage is reported per community and per age; low-coverage areas (law, the humanities) and parametric-only (not yet directly-fitted) fields are flagged rather than shown with false confidence. Communities outside the calibrated seed are served with the universal layer only and labeled calibration-pending.

## 9. Why it resists gaming

*Status: this section states QaL's intended gaming-resistance, not all of which the current prototype implements. Live now: the per-paper percentile basis (so volume and salami-slicing do not help), decide-late intervals for calibrated communities, a fixed and reported reference class with no user-selectable headline, the no-single-author-score rule, and open code. Not yet built: self-citation exclusion, authority-weighting of citations, and any usage or attention signal — so today's observed percentile rests on raw OpenAlex citation counts. Read the safeguards below as the target the design is built toward, not a claim about the prototype.*

Following the Leiden Manifesto (Hicks et al., 2015) and DORA (2013), robustness comes from construction and transparency, not secrecy. Self-citations are excluded; citations are authority-weighted so peripheral or mutually-citing clusters count for little; usage signals inform only the timing of the posterior, never its level; QaL is per-paper and percentile-based, so producing many weak papers raises no one's score; the reference class is fixed and reported; and deciding late means a transient spike widens uncertainty rather than locking in a high estimate. The method and inputs are open and auditable. Deliberately, QaL never rolls a scholar up into a single number; quality is reported per paper.

## 10. Limits and open questions

- **Marginal, not conditional, coverage.** The conformal correction guarantees coverage on average over the calibration distribution. Computing the radius per age strengthens it toward conditional validity, but we do not claim exact coverage within every (age, observed-percentile) cell.
- **Exchangeability is approximate.** The conformal guarantee assumes exchangeable calibration data; vintages are not exactly exchangeable, which is the original problem. Deriving the radius by leave-one-vintage-out makes the estimate robust to cross-vintage variation rather than assuming it away, so the guarantee is empirical (validated by the back-test), not a clean finite-sample theorem.
- **Horizon truncation.** "Eventual" is fixed at *H* = 10 years; citations accrue beyond that. The convention is applied identically in fit and test, so it does not bias coverage, but the estimand is "percentile at ten years," not "percentile at infinity."
- **Sampling for large communities.** 1803 (about 716k works) and 1802 (about 526k) were calibrated from uniform random samples of 10,000 works per cohort; 1800 (about 32k) was pulled in full. Sample-based estimates carry about 1% sampling error, immaterial at these sizes, but are labeled as such.
- **Reference class.** The current calibration is on field-and-vintage cohorts, a stand-in for the official synthetic-field blend; recalibrating on the staged blend may shift the conformal radii.
- **Non-stationarity.** Calibration learned on older cohorts is applied to newer ones; it drifts slowly, so we re-fit periodically and re-test by comparing the mapping across vintages.

## 11. References

All entries verified against the primary record.

- Angelopoulos, A. N., & Bates, S. (2021). *A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification.* arXiv:2107.07511. (Also Foundations and Trends in Machine Learning, 2023.)
- Boyack, K. W., & Klavans, R. (2010). Co-citation analysis, bibliographic coupling, and direct citation: Which citation approach represents the research front most accurately? *JASIST*, 61(12), 2389–2404.
- DORA (2013). *San Francisco Declaration on Research Assessment.*
- de Solla Price, D. J. (1970). Citation measures of hard science, soft science, technology, and nonscience. In *Communication among Scientists and Engineers* (the Price Index).
- Glänzel, W., & Schubert, A. (1988). Characteristic Scores and Scales in assessing citation impact. *Journal of Information Science*, 14(2), 123–127.
- Hicks, D., Wouters, P., Waltman, L., de Rijcke, S., & Rafols, I. (2015). The Leiden Manifesto for research metrics. *Nature*, 520, 429–431.
- Hutchins, B. I., Yuan, X., Anderson, J. M., & Santangelo, G. M. (2016). Relative Citation Ratio (RCR). *PLoS Biology*, 14(9), e1002541.
- Persson, O. (1994). The intellectual base and research fronts of JASIS 1986–1990. *Journal of the American Society for Information Science*, 45(1), 31–38.
- Radicchi, F., Fortunato, S., & Castellano, C. (2008). Universality of citation distributions. *PNAS*, 105(45), 17268–17272.
- Romano, Y., Patterson, E., & Candès, E. J. (2019). Conformalized Quantile Regression. *Advances in Neural Information Processing Systems (NeurIPS)*, 32, 3538–3548. arXiv:1905.03222.
- Stringer, M. J., Sales-Pardo, M., & Amaral, L. A. N. (2010). Statistical validation of a global model for the distribution of the ultimate number of citations accrued by papers published in a scientific journal. *JASIST*, 61(7), 1377–1385.
- Vovk, V., Gammerman, A., & Shafer, G. (2005). *Algorithmic Learning in a Random World.* Springer. (2nd ed., 2022.)
- Waltman, L. (2016). A review of the literature on citation impact indicators. *Journal of Informetrics*, 10(2), 365–391.
- Waltman, L., & Schreiber, M. (2013). On the calculation of percentile-based bibliometric indicators. *JASIST*, 64(2), 372–379.
- Waltman, L., & van Eck, N. J. (2012). A new methodology for constructing a publication-level classification system of science. *JASIST*, 63(12), 2378–2392.
- Wang, D., Song, C., & Barabási, A.-L. (2013). Quantifying long-term scientific impact. *Science*, 342(6154), 127–132.

*Supporting internal documents: QaL_spec.md (the build specification), data_sourcing.md (the open-data spine and terms of use), and calibration_backtest_note.md (the full back-test methodology).*
