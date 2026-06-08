# QaL Level 0: Specification for a Robust, Defensible Quality Metric

*Spec, June 2026. Goal: define QaL precisely enough to build it, starting with Level 0 (the Lens): the metric computed entirely from the open public record, no participants, no human review. Grounded in the verified bibliometrics (Leiden Manifesto; percentile classes; Relative Citation Ratio; MNCS; Characteristic Scores and Scales) and the open data spine (data_sourcing.md). Build it once, defensibly, then layer the rest.*

## 1. Purpose and scope

QaL Level 0 estimates, for any indexed paper, its eventual quality as a percentile within a stated field-and-vintage reference class, and reports that estimate honestly with uncertainty. It is computed from public data alone and therefore has no cold-start. In scope: the estimand, the reference class, the input signals, the estimator, gaming-resistance, the output record, and validation. Out of scope for Level 0: human review, conferred tiers (Refereed, Canon), correctness certification beyond retraction flags, and any participant-supplied data. Those are later bundles.

QaL has two layers with different scope, and only one of them is scope-bound. The universal report (metadata, the observed within-class percentile, the retraction flag, the links, and the co-citation-neighborhood context) is computable for any indexed paper and has no cold-start. The calibrated posterior over eventual percentile is scope-bound to communities for which we have fit and back-tested the early-to-eventual mapping (Section 5). The seed calibrated communities are the Decision Sciences subfields that cover this department; outside them a paper is still pulled and reported, but its eventual-percentile posterior is flagged calibration-pending rather than shown with false confidence.

## 2. The estimand (what QaL is, precisely)

For a paper p evaluated at time t, define the target as the paper's **eventual percentile** r∞(p) within its field-and-vintage cohort, on the dimension of recognized value (impact), where "eventual" means at a fixed long horizon (for example 10 years after publication). r∞ is a number in [0,100].

QaL is not a point claim about r∞; it is a **calibrated belief** about r∞ given the evidence available at time t, because most of r∞ is realized after t. QaL therefore reports three things, always against a stated reference class:

- a point estimate: the posterior median of r∞;
- a 90% interval: the 5th and 95th percentiles of the posterior;
- class probabilities: P(r∞ ≥ c) for the NSF/Leiden cut points c ∈ {50, 75, 90, 95, 99}.

This is the honest object the deck promises: a point, an interval, and bucket probabilities, decided late.

## 3. Reference class

Every QaL is relative to an explicit reference class, reported with the estimate:

- **Field (official: the co-citation neighborhood).** The headline QaL normalizes against the paper's co-citation neighborhood, the RCR construction (Hutchins et al. 2016), which benchmarks it against the papers it actually travels with in reference lists. This is the official reference class because it is robust to OpenAlex's single-primary-field misclassification, which is severe for interdisciplinary work: our worked example (an LLM-for-innovation paper) is a near three-way tie across Computer Science, Social Sciences, and Business, and OpenAlex's primary label happened to be Computer Science. Where co-citation data is too thin (very new or sparsely cited papers), fall back to a score-weighted blend across the paper's OpenAlex topic fields.
- **Vintage.** Publication year. Because within-year exposure differs by month, record publication month and, where cohorts are large enough, normalize within a narrower window (the equal-exposure refinement from the early-signal study).
- **Cohort size n** is reported so the reader knows the base.
- **Robustness panel (required display).** Always show QaL across several reference classes side by side: the co-citation neighborhood (headline), all-fields, each detected OpenAlex field, and the field-weighted blend, each with a leaderboard link to the top of that context. Agreement across classes signals a robust estimate; divergence flags a field-sensitive one and is itself information. The official number is fixed (the co-citation neighborhood) to prevent reference-class shopping; the panel and any user-selected class are for exploration only.

QaL is never a single context-free number; the reference class travels with it.

## 4. Input signals (all from the open record)

Grouped by role. Each signal lists source and definition; see data_sourcing.md for terms.

**A. Citation-based (the spine).**
- Field-and-vintage citation percentile: the paper's rank, within its cohort, of cumulative citations to date (the empirical-CDF percentile transform, with the uncited atom handled explicitly). Source: OpenAlex.
- Authority-weighted citations: PageRank/eigenvector centrality on the open citation graph, so a citation from a central paper counts more than one from a peripheral or self-citing source. Source: OpenCitations / Crossref references. (Phase 2; Level 0 may start with plain counts and add this.)
- Self-citations excluded; consider fractional counting for heavily co-authored work.

**B. Early-signal / usage (where available, to inform the posterior, not as a separate score).**
- Early citation accrual by age (the input to the decide-late posterior, Section 5).
- Downloads where openly available: bioRxiv/medRxiv API, RePEc/LogEc. Not available for SSRN (terms).

**C. Correctness / integrity (penalties, asymmetric).**
- Retraction, correction, expression-of-concern flags. Source: Retraction Watch via Crossref. A retraction overrides QaL (flagged/withdrawn); a correction annotates.
- (Optional) penalty for heavy citation of retracted work.

**D. Identity / eligibility (a gate, not a score).**
- ORCID-authenticated authorship. Level 0 computes QaL for all indexed works regardless; identity matters once submission and tiers exist.

## 5. The estimator (how signals become QaL with uncertainty)

Two layers. The design intent: anchor on robust, field-normalized observed impact, and let uncertainty be driven by how much of the eventual signal has plausibly arrived, calibrated from history.

**Layer A, observed percentile.** Compute r_obs(p, t): the paper's percentile within its cohort by cumulative (authority-weighted, self-excluded) citations as of t. Use the percentile/probability-integral transform; assign the uncited atom a single shared rank.

**Layer B, calibrated posterior over eventual percentile.** Because r_obs at age a understates or overstates r∞, map (r_obs, age a, field) to a posterior distribution over r∞, calibrated on historical cohorts. Concretely, estimate from past data (for example all OpenAlex papers in the field published 2008–2015, observed to a long horizon) the conditional distribution

  r∞ | (r_obs at age a, field),

by binning on (age, r_obs) or by quantile regression. The posterior is that empirical conditional distribution. From it read the median (point), the 5th/95th percentiles (90% interval), and the mass above each cut point (class probabilities).

Properties this gives for free:
- Young papers get wide intervals (little of r∞ has arrived); old papers get tight ones (r_obs ≈ r∞). This is the decide-late behavior, derived from data rather than asserted.
- The interval width at age a is governed by the measured early-signal validity (the ρ(a) curve from the early-signal study: ρ ≈ 0.5 at one year, rising toward 1). So the metric's honesty about young work is empirically anchored.
- Correctness penalties (Section 4C) shift or floor the posterior.

**Calibration scope (which communities we calibrate).** Calibration is the only scope-bound part of QaL. Any paper in OpenAlex can be pulled and reported with the universal layer (Section 1) without calibration. What is scope-bound is the Layer-B posterior over r∞, because that mapping must be learned from a community's own matured history, and the early-to-eventual relationship genuinely differs by field: operations resolves faster than psychology or economics, so a single pooled mapping would be miscalibrated. We therefore calibrate per community.

The seed calibration set is the Decision Sciences subfields that cover the OID department: Management Science and Operations Research (1803), Information Systems and Management (1802), and General Decision Sciences (1800). Optional cheap extensions by the same procedure are Statistics, Probability and Uncertainty (1804, the fourth Decision Sciences subfield, which also catches research-methods work) and Management of Technology and Innovation (1405).

A faculty coverage test confirms the consequence of this choice. For seven OID members (Schweitzer, Milkman, Watts, Knox, Simmons, Bastani, Yu), checking the OpenAlex primary topic of their recent ~120 papers each, the share landing inside the seed subfields was: Bastani 33% (operations, dominated by Advanced Bandit Algorithms in 1803, well inside), Schweitzer 30%, Simmons 24%, Milkman 21% (the behavioral core, only partially inside because much of it is filed under Applied and Social Psychology, Health, and research methods), Watts 8% (computational social science, networks and misinformation), Knox 1% (political methodology and causal inference), Yu 8% (algorithmic theory, out of scope by design). These shares measure cohort membership for calibration, not whether a paper can be scored.

By this scope decision, papers outside the calibrated subfields are still scored and reported universally, but served neighborhood-only and calibration-pending: the observed standing and the co-citation-neighborhood context display, while the calibrated eventual-percentile posterior (point, interval, bucket probabilities) is withheld or flagged low-confidence until that community is calibrated. Standing up an additional community (for example Applied and Social Psychology, or a computational-social-science bundle to bring in Watts and Knox) is the same pull-and-fit procedure run on that community's matured history: deferred, not precluded.

This estimator is deliberately simple, transparent, and reproducible. It is not a black box; the inputs and the calibration are public.

## 6. Decide-late and the tier thresholds (interface to later bundles)

QaL Level 0 only reports the estimate. But it is designed so the later tiers are thresholds on it:
- a tier requires a confidence level (for example 90%) that r∞ clears a cut point. Refereed ≈ P(r∞ ≥ 75) ≥ 0.9; a Canon-like level ≈ P(r∞ ≥ 95) ≥ 0.9.
- A young paper rarely clears these (wide posterior); an established one does. Deciding late is enforced by requiring confidence, not by a waiting rule.

## 7. Gaming-resistance (by design, not secrecy)

Per the Leiden Manifesto, the method and inputs are transparent and auditable; robustness comes from construction. For each known attack:
- Self-citation inflation: self-citations excluded.
- Citation cartels / low-quality citations: authority-weighting discounts citations from peripheral or mutually-citing clusters.
- Download/attention inflation: usage feeds only the posterior's timing, never the level; the level is citation-based and authority-weighted.
- Salami-slicing / volume: QaL is per-paper and percentile-based, so producing many low-percentile papers does not raise any paper's QaL.
- Transient spikes: deciding late (the posterior) means a short-lived burst widens uncertainty rather than locking in a high estimate.
- Reference-class shopping: the reference class is fixed by field-and-vintage and reported; it is not author-selectable.
The exact weights are public and auditable; they may be governed and periodically reviewed, but they are not secret. Security-by-obscurity is rejected.

## 8. Data sources and cadence

Primary key: OpenAlex Work ID, plus DOI and arXiv ID (data_sourcing.md). Citations and cohorts: OpenAlex; references and authority graph: OpenCitations and Crossref. Identity: ORCID. Preprints and early usage: arXiv (OAI-PMH/S3), bioRxiv (API), RePEc/LogEc. Correctness: Retraction Watch via Crossref, iCite where applicable. All open, all within terms; SSRN reached only indirectly via DOIs in the open aggregators. Refresh monthly; QaL is versioned and timestamped.

## 9. Output: the QaL entity record

Each rated entity is a thin record pointing to the canonical location(s). Sketch:

```
{
  "qal_id": "openalex:W2192203593",
  "doi": "10.1287/mnsc.xxxx",
  "locations": ["doi.org/...", "arxiv.org/abs/...", "ssrn.com/..."],
  "reference_class": {"field": "subfields/1803", "field_label": "Management Science & OR",
                      "vintage_year": 2015, "vintage_month": 1, "n": 8498},
  "qal": {"point": 96, "ci90": [90, 99],
          "class_prob": {"ge50": 1.00, "ge75": 0.99, "ge90": 0.93, "ge95": 0.62, "ge99": 0.21}},
  "inputs": {"cum_citations": 142, "authority_weighted": true, "self_excluded": true,
             "obs_percentile": 95, "age_years": 11, "retraction_flag": false},
  "method_version": "qal-0.1", "computed_at": "2026-06-08", "data_snapshot": "openalex-2026-05"
}
```

Transparency requires that `inputs` and `method_version` be published with every estimate, so anyone can reproduce it.

## 10. Validation and acceptance criteria (what makes it defensible)

Level 0 ships only when it passes:
1. **Calibration.** On held-out historical cohorts, the 90% interval covers realized r∞ about 90% of the time, across ages and fields. (Back-test on 2008–2015 cohorts observed to 2024+.)
2. **Concordance at maturity.** For old papers, QaL agrees with accepted field-normalized metrics (RCR, MNCS, percentile classes).
3. **Manipulation robustness.** Simulated self-citation and cartel attacks move QaL negligibly; download inflation does not move the level at all.
4. **Reproducibility.** The estimate recomputes from the published inputs and snapshot.
5. **Coverage honesty.** Coverage is reported per field; low-coverage fields (law, humanities) are flagged rather than scored confidently. Papers outside the calibrated communities (Section 5) get the universal layer, but their eventual-percentile posterior is flagged calibration-pending rather than shown with false confidence.

## 11. Architecture and caching

The dividing line is clean: the cheap metrics can run on demand; the graph metrics cannot, so something is precomputed regardless, and caching the rest is nearly free.

**Cheap, feasible on the fly (~1–3 s per paper):** fetch the work record (one OpenAlex call); compute the field-and-vintage percentiles, which are exact with just two count queries each (cohort size, and count with more citations), no sampling; read the interval and bucket probabilities from a precomputed calibration table; check the retraction flag. No database required for this path.

**Must be precomputed (graph computations, not request-time):** the co-citation neighborhood (RCR), which needs the citing works and their reference lists assembled (dozens to hundreds of calls per paper), and authority-weighting (PageRank), which is a whole-graph computation. These run in batch and are cached, keyed by OpenAlex Work ID.

**Key optimization:** cohort denominators are shared across every paper in a field-year, so precompute, per (field, year), a small citation-count → percentile table. Then a paper's percentile is an O(1) lookup rather than live count queries. These tables only shift with the monthly OpenAlex refresh.

**Caching policy:** store the final QaL record per Work ID with a timestamp; serve read-through (return the cached value instantly, recompute on a miss or when stale); refresh monthly to match the OpenAlex snapshot cadence, since citations move slowly. Caching also keeps us a good OpenAlex citizen by not re-hitting the API on every view.

## 12. Three versions: POC, MVP, V1.0

**POC — prove the page and the robustness check, one field, on the fly.**
- Architecture: no database. Live OpenAlex calls for the work plus the field percentiles; a static calibration-table file; the co-citation neighborhood shown illustratively (not computed).
- Scope: the paper view (already mocked as paper-mvp.html), the cross-reference-class robustness strip with exact observed percentiles, leaderboard links (constructed OpenAlex URLs), the evidence block, and the links plus a Zenodo "deposit a new record" affordance.
- Deferred: co-citation neighborhood (illustrative), authority-weighting, caching, multi-field, accounts.
- Acceptance: loads in a few seconds for any OpenAlex Work ID in the seed field; numbers reproducible.

**MVP — the real headline metric for one or a few fields, cached.**
- Architecture: a small datastore (Postgres or DuckDB) keyed by Work ID; read-through cache with timestamps; nightly/monthly batch jobs that build the per-cohort percentile tables and compute the co-citation neighborhood (RCR) and the calibrated Layer-B posterior for covered papers.
- Scope: everything in the POC, plus the real co-citation neighborhood as the headline, the back-tested posterior, the retraction overlay (Retraction Watch via Crossref), a read API and entity JSON, and "post a new record" implemented as deposit-to-Zenodo-and-track (no hosting, no archiving obligation).
- Seed calibrated communities: the Decision Sciences subfields covering the department, Management Science & Operations Research (1803), Information Systems & Management (1802), and General Decision Sciences (1800), where coverage is good and we already have a working OpenAlex path and a 2015 MS&OR cohort. Papers outside these are served universally but neighborhood-only and calibration-pending (Section 5).
- Deferred: authority-weighting at scale, full-corpus coverage, the community/review (Refereed) layer.
- Acceptance: calibration back-test passes (the 90% interval covers ~90% of realized outcomes); self-citation and cartel simulations move QaL negligibly; coverage reported per field.

**V1.0 — the Lens done well at scale.**
- Architecture: ingest the OpenAlex bulk snapshot into an owned store, dropping the live-API dependency and its rate limits; full-corpus batch compute of cohort tables, co-citation neighborhoods, and authority-weighting (PageRank); monthly refresh on the snapshot; QaL served from cache; a public read API and the web UI.
- Scope: co-citation headline plus authority-weighted citations plus the all-fields and per-field robustness panel plus the correctness overlay; QaL-ranked leaderboards (ranked by QaL, not raw citations) as a public good; user-selectable reference class for exploration with the official number fixed; open export of QaL and any certifications.
- Hooks, not scope: the community/Refereed layer is the next bundle and is explicitly out of V1.0.
- Acceptance: calibration holds across fields and ages; coverage limits (law, humanities) reported honestly; manipulation-robustness audited; reproducible from the snapshot; low-latency from cache.

**Interface requirements (all versions).** The web surfaces (the paper, author, and explore views, and the About page) must be responsive and mobile-friendly: a fluid layout that collapses to a single column below roughly 700px, tap-friendly controls, type legible on a phone without zooming, and wide data tables that scroll horizontally within their container rather than overflowing the page. The POC and MVP acceptance criteria include correct rendering on a phone-width viewport (about 380px) in addition to desktop.

**Author display.** List every co-author when a work has fewer than 11 authors (i.e. ten or fewer); for eleven or more, show the first author followed by "et al." This keeps full credit visible for normally-authored work while avoiding unreadably long bylines on large-collaboration papers.

## 13. Open parameters to settle before building

- Field granularity: settled. The co-citation neighborhood is the official scoring reference class (Section 3); the OpenAlex Decision Sciences subfields covering the department define the seed calibration cohort (Section 5).
- Vintage window: full year versus narrower (equal-exposure) windows.
- Counting: full versus fractional; exact self-citation rule; authority-weighting scheme and whether it is in the Level 0 MVP or Phase 2.
- The uncited atom: single shared rank versus a small spread.
- Long-horizon definition for r∞ (10 years? field-specific cited-half-life?).
- Confidence level for tier thresholds (90%?), set now so Level 0 outputs are tier-ready.

## 14. References (verified)

- Hicks, Wouters, Waltman, de Rijcke & Rafols (2015), "The Leiden Manifesto for research metrics," *Nature* 520:429–431.
- Hutchins, Yuan, Anderson & Santangelo (2016), "Relative Citation Ratio," *PLoS Biology* 14(9):e1002541.
- Glänzel & Schubert (1988), "Characteristic Scores and Scales in Assessing Citation Impact," *Journal of Information Science* 14(2):123–127.
- CWTS Leiden Ranking (MNCS, field-and-year normalization); National Science Board, *Science & Engineering Indicators* (NSB-2025-7), percentile classes.
- Radicchi, Fortunato & Castellano (2008), *PNAS* 105(45):17268–17272 (universality of the rescaled citation distribution).
- Brody, Harnad & Carr (2006), *JASIST* 57(8):1060–1072; Perneger (2004), *BMJ* 329:546–547 (early signal predicts later citations).
- San Francisco Declaration on Research Assessment (DORA, 2013).
- Data sources and terms: see data_sourcing.md.
