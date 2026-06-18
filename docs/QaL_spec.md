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

- **Field (official: the synthetic field).** The headline QaL normalizes against a *synthetic field*: a vintage-matched blend of OpenAlex (subfield, year) cohorts whose mixture weights describe the focal paper's intellectual community, with the percentile taken over the blended full population including the uncited atom (§5). The blend, not a fixed subject category, is the official reference class because it is robust to OpenAlex's single-primary-field misclassification, which is severe for interdisciplinary work: our worked example (an LLM-for-innovation paper) is a near three-way tie across Computer Science, Social Sciences, and Business, and OpenAlex's primary label happened to be Computer Science. The mixture weights are obtained by a **staged construction** (§5, Synthetic-field weights): from the focal paper's own references at and shortly after posting (no cold start, available with zero citations), weighted toward the **research front** so that recent, specific references count more than old canonical ones (Persson 1994; Boyack & Klavans 2010; the Price Index, de Solla Price 1970), migrating to the co-citation community as citing papers accrue (the RCR-style community view, Hutchins et al. 2016). Where the bibliography is unavailable the construction descends a fallback chain rather than collapsing to OpenAlex's single label — the co-citation community when the paper has any citers, then a content-and-authorship prior (the paper's own topics blended with its authors' recent subfield mixtures) for a brand-new paper with neither references nor citers, and only the focal paper's own single (subfield, vintage) cohort as a last resort — so any indexed paper is placed against a blended community. The units: OpenAlex organizes the literature as 4 domains, 26 fields, 252 subfields, and about 4,500 topics; the top three levels are the Scopus journal classification, and the topics are citation-network clusters that each map into exactly one subfield (for example, the field Decision Sciences contains the subfields Management Science & Operations Research and General Decision Sciences, which contain topics such as Advanced Bandit Algorithms and Decision-Making and Behavioral Economics). QaL operates at the **subfield** level: the blend, the percentile tables, and the calibration are all per subfield, never per topic.
- **Vintage.** Publication year. Because within-year exposure differs by month, record publication month and, where cohorts are large enough, normalize within a narrower window (the equal-exposure refinement from the early-signal study).
- **Cohort size n** is reported so the reader knows the base.
- **Robustness panel (required display).** Always show QaL across several reference classes side by side: the synthetic field (headline), all-fields, each detected OpenAlex field, and the field-weighted blend, each with a leaderboard link to the top of that context. Agreement across classes signals a robust estimate; divergence flags a field-sensitive one and is itself information. The official number is fixed (the synthetic field) to prevent reference-class shopping; the panel and any user-selected class are for exploration only.

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

**Layer A, observed percentile.** Compute r_obs(p, t): the paper's percentile within its cohort by cumulative (authority-weighted, self-excluded) citations as of t, via the percentile/probability-integral transform. *(Status: authority-weighting and self-citation exclusion are Phase 2; the current prototype ranks on raw OpenAlex citation counts.)*

**Denominator rule (the uncited atom).** The percentile is taken over the **full population, cited and uncited**, never the cited papers alone. Roughly half of every cohort is uncited (in the seed, Management Science & OR is 53.6% uncited at maturity and about 60% at age two; General Decision Sciences 36% and 56%), so ranking only among cited papers would inflate every percentile and, worse, put the official neighborhood number on a different denominator from the field number, breaking the robustness panel. The uncited mass is countable, not unobservable, but the co-citation neighborhood cannot serve as the comparison cohort directly: it is a popularity-biased, cited-only sample (a paper is co-cited with the focal in rough proportion to its own citation count, so the neighborhood over-represents highly-cited papers and by construction contains no uncited papers). We therefore use the neighborhood only for the topic mixture of the focal paper's community, which it estimates with low bias, and compute the percentile against the representative full population of that mixture, which contains the uncited papers and so supplies the atom directly. The uncited are tied and receive the **mid-rank**, 100 · p₀/2. A focal paper that is itself uncited has no co-citation neighborhood of its own; it is served the universal field-and-vintage percentile (within the atom) with the neighborhood headline marked calibration-pending. The identical full-population denominator is used when r∞ is computed for calibration (Layer B), so the atom is present in the fit and in the back-tested coverage.

**Precise computation.** The focal paper's references and, later, its citing community are used only to set the topic-mixture weights of the synthetic field, never as the cohort to rank against. The percentile is computed against the full-population blend of those topics' cohorts.

*Synthetic-field weights (staged).* Let w_t be the weight on topic t, normalized so that Σ_t w_t = 1.

- **Reference-based stage (cold start; works with zero citations).** From the focal paper's referenced works, read each reference's subfield t (its primary topic maps to exactly one subfield) and publication year y_i. Weight each reference toward the research front by recency: g_i = exp(−max(0, v − y_i)/τ_f), where v is the focal paper's year and τ_f = h_f / ln 2 is a decay timescale set by the field's cited half-life h_f (default: one global h until per-field values are available, §7; clip ages below 0). Then w_t^ref = Σ_{i in subfield t} g_i, normalized over subfields. Recent, specific references therefore dominate the placement while old canonical references contribute to the base without governing it (research-front vs intellectual-base: Persson 1994; bibliographic coupling recovers the front best: Boyack & Klavans 2010; recency-of-references as a front measure: de Solla Price 1970). The ~4,500 topics are not enumerated for the weighting; they are only the mechanism by which OpenAlex assigns each reference its subfield, plus a display aid. (A reference whose topics span several subfields may optionally be split fractionally by its topic shares rather than assigned wholly to its primary subfield — a marginal refinement, off by default.) An optional inverse-popularity downweight of ubiquitous references is **off by default**, pending validation, because the IDF-on-citations evidence is mixed. If fewer than N_min usable references remain (default 5), the reference stage is skipped and the construction descends the fallback chain below.
- **Community stage (as citing papers accrue).** Compute w_t^cc from the co-citation neighborhood's topic mixture (the community's framing, harder to game).
- **Migration.** w_t = (1 − λ) · w_t^ref + λ · w_t^cc, with λ rising from 0 toward 1 as the citing set grows (default λ = c / (c + k), c = number of citing papers, k a constant, e.g. 20). Early placement comes from the bibliography; mature placement from the community; the two should largely agree, and disagreement is itself informative.
- **Fallback chain (robust placement for any paper).** A working paper fresh on SSRN often has neither a bibliography OpenAlex can read nor any citers yet. Rather than collapse to OpenAlex's single primary label — the misclassification the synthetic field exists to correct — the construction descends one rung at a time: (i) **co-citation**, w_t^cc above, used on its own whenever the paper has citers even with no bibliography of its own; (ii) **content-and-authorship prior**, when the paper has neither usable references nor citers — blend the focal's own OpenAlex topic mixture (its topics' subfields, weighted by topic score) with the recency-weighted subfield mixtures of its authors' recent bodies of work (their last ~50 works each, same recency weight g_i), each author first normalized to unit mass so a prolific co-author does not dominate, combining the two components by α (default α = 0.55 on the paper's own topics; lean fully on whichever component exists when one is empty); (iii) **single subfield**, the focal paper's own primary subfield, only as the last resort when even the prior is empty. Because every rung produces a subfield *mixture* and the percentile is always taken over the full-population blend of that mixture (below), any indexed paper — including one posted minutes ago, with no references and no citations — is placed against a genuine blended community rather than a single guessed field. The basis actually used (references, co-citation, or author-prior) travels with the record so the placement is auditable.

*Reference distribution.* D = Σ_t w_t · cohort(t, v): the weight-blended full (subfield, vintage) cohorts at the focal paper's year v (vintage-normalized, since p₀ and citation levels are age-dependent; each cohort includes its uncited papers). Cohorts are at the subfield level, which is dense enough for stable percentiles and calibration; topic-level cohorts are too thin.

*Full-population percentile.* r_obs is the focal paper's percentile within D, ties (the uncited atom included) at the mid-rank, or, preferably, the fractional assignment of Waltman & Schreiber (2013), which handles the large tie mass cleanly. Compute it as a **weight-average of per-cohort percentiles**: for the paper's citation count c, r_obs = Σ_t w_t · pct_t(c), where pct_t(c) is its percentile (same tie convention, full population including uncited) against subfield t's vintage-v citation distribution. This equals its percentile in the pooled blend D **exactly, not approximately**, because a mixture's CDF is the weighted average of its components' CDFs and the mid-rank convention is linear in the same way; "rank c in the pool" and "weight the per-subfield percentiles" give the identical number. Each pct_t(c) is an O(1) lookup in the per-(subfield, vintage) percentile table, so r_obs is a weighted sum of a handful of lookups, not a query per cohort member. There is no rank-among-neighbors step and no rescaling: the uncited atom and its mass p₀ = Σ_t w_t · p₀(t, v) emerge from the blend, each p₀(t, v) being the zero-citation share of that cohort (the bottom breakpoint of the percentile table; no extra queries). The identical full-population blend and tie convention are used when r∞ is computed for calibration (Layer B), so the atom is present in the fit and in the back-tested coverage; because the convention is a monotone relabeling, coverage is expected to be stable and should be re-validated.

*Fallback.* A paper with too few usable references and no citing community uses its own (subfield, vintage) cohort, the single-topic special case of the blend.

*Retained vs given up.* The synthetic field keeps misclassification robustness (the weights reflect the true intellectual community, not a single OpenAlex label) but gives up sub-topic granularity, which cannot support an unbiased percentile in any case; a finer representative reference class (citation-network clusters, Waltman & van Eck 2012, or embeddings, in either case including uncited works) is a future refinement.

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
  "authorships": [{"name": "Karl T. Ulrich", "openalex_id": "A5040079549",
                   "orcid": "0009-0000-4781-9230"}, "..."],
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

The record carries **per-author identity** in `authorships` (OpenAlex Author ID, plus ORCID where available), not just display strings, so every author name can resolve to that author's page. The byline *display* rule abbreviates long lists (all co-authors when fewer than eleven, otherwise the first author and "et al."), but the underlying identities are retained for linking.

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

**Key optimization:** cohort denominators are shared across every paper in a (subfield, year), so precompute, per (subfield, year), a small table giving the citation count at each percentile (the empirical CDF). Then a paper's percentile is an O(1) lookup rather than live count queries. For instance, in Management Science & Operations Research, 2015, about 54% of the ~43,000 papers are uncited, so the bottom half of that table is one tied value and the top percentiles climb steeply into the heavy tail. These tables, one per (subfield, year), plus the per-subfield calibration, are essentially all that must be precomputed; the per-paper weighting and ranking run on the fly. The tables only shift with the monthly OpenAlex refresh.

**Caching policy:** store the final QaL record per Work ID with a timestamp; serve read-through (return the cached value instantly, recompute on a miss or when stale); refresh monthly to match the OpenAlex snapshot cadence, since citations move slowly. Caching also keeps us a good OpenAlex citizen by not re-hitting the API on every view.

**Coverage rollout (staged sampling).** To cover many subfields under the OpenAlex daily quota, before the bulk snapshot (V1.0), build breadth-first and refine, labeling confidence honestly throughout.

- *Percentile tables, skeleton then fill.* For every (subfield, year), first pin an exact skeleton with a few count queries: cohort size n, uncited fraction p₀ (count of `cited_by_count:0`), and a handful of upper-tail thresholds (counts with `cited_by_count:>X` on a fixed X-ladder). This is exact, cheap, and covers all cohorts immediately. Then refine the interior CDF with **uniform random** samples of growing size (1k, then 5k, then 10k per cohort). Never sample top-N by citations; that reintroduces the popularity bias. The tail anchors stay exact from the count queries regardless of sample size.
- *Calibration, parametric then fitted.* Day-one calibration for a subfield is the two-parameter family (§7): estimate its citation half-life and tail from a small matured-cohort sample and shrink toward a discipline-level prior, giving every subfield a defensible posterior at once. As samples grow over the matured 2008–2016 cohorts, upgrade from the parametric estimate to a directly fitted (age, observed-percentile) mapping with per-age conformal widening, sharpening the thin tail cells last. Only a directly fitted, leave-one-vintage-out back-tested subfield is **gate-passed**.
- *Confidence tag.* Every served QaL carries a coverage tag that rises with the data behind it: `parametric` (day-one, shrinkage), `fitted` (direct cells), `gate-passed` (LOVO coverage ≈ 0.90). Never claim the back-test for a subfield that has not earned it; the calibration-pending and illustrative labels already in the UI carry this.
- *Adaptive budget.* Refinement is not uniform. Measure how much each subfield's estimate moves from 1k → 5k → 10k; stop refining the ones that have stabilized (usually everything but the tail) and spend the remaining quota where the estimate is still shifting or where traffic and audience demand it. Spend the early budget on the OID department's subfields (the first audience), then broaden.
- *Snapshot supersedes.* Once the OpenAlex snapshot is ingested (V1.0) the deep pass becomes a local group-by and the sampling-budget question largely disappears; staged sampling is the bridge until then.

**Author view and bylines.** Every author name shown on a paper — on the paper page and in the explore/record tables — is a **hyperlink to that author's page**, so a reader can pivot from any work to any of its displayed authors. This requires bylines to carry per-author identity (§9 `authorships`: OpenAlex Author ID, ORCID where available), not just display strings. The author page is built **on the fly for any author**, the same cheap-path pattern as the paper page: one OpenAlex call for the author entity, one for their works, then each work shown with its QaL — read from the cache where computed, universal/calibration-pending otherwise — ranked, with the author's fields and vintages summarized. No pre-seeding or author "ingest" is required; on-the-fly construction generalizes and retires that step (the former M9). Consistent with the estimand and gaming-resistance, the author page reports a **distribution of per-paper QaL and never a single rolled-up author score**. Identity is anchored on the OpenAlex Author ID (ORCID where present) for disambiguation; where a name resolves ambiguously, the link uses the work's own authorship record rather than a name search.

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

### Current state (as built, June 2026)

This section is the baseline; the remaining work below is incremental to it. See `BUILD_BACKLOG.md` for item-level status.

Live on academic-ledger.org. The POC is complete. The MVP is largely built: the Neon datastore and schema (`works`, `cohort_percentiles`, `calibration_models`, `qal_records`, `authors`, `author_works`, `synthetic_field`, `subfields`); ingest of the seed communities (1800 in full, 1803 and 1802 as 10k-per-cohort uniform samples); per-(subfield, year) percentile tables under the full-population mid-rank rule; the Layer-B calibration with per-age split-conformal widening, back-tested at about 0.90 to 0.91 leave-one-vintage-out coverage across 1803/1802/1800; the synthetic-field reference class (recency-weighted staged blend) computed per paper and prefilled for the top ~480 seed and leaderboard papers; `compute_qal.py` joining works + percentiles + calibration + synthetic field into `qal_records` carrying both the field and synthetic metrics; the read API; and the paper, author, and explore pages, with dual sortable QaL columns (field and synthetic, official highlighted), the synthetic-field composition on the paper page, the calibration-pending UX, and a formatted citation.

Remaining MVP increments: wire the monthly refresh cron (M6; a launchd one-shot currently resumes the synthetic prefill after the daily OpenAlex quota resets, a stopgap, not the cron); the retraction overlay and the Zenodo deposit affordance (M7); on-the-fly author pages with clickable, identity-carrying bylines so the author page works for any author without pre-seeding (M9, superseding the earlier "author ingest" framing); and the small UI item of dropping the Access (oa_status) cell from the paper evidence grid (U5). The synthetic field is also computed **on the fly** for any paper not in the prefilled set, via the full fallback chain (references → co-citation → content-and-authorship prior) — behind a behavior gate: a client-triggered, cached `POST /api/synthetic/:oaid` (run by a real browser after the page mounts), never on a server GET, so flat crawler views don't trigger the metered compute. The single-field stand-in remains only as the rare last resort. V1.0 (OpenAlex snapshot ingest, full-corpus compute, PageRank, public API) is the scale step — its **universal-layer cohort build is now done**: `pipeline/factory.py` makes one in-region DuckDB pass over the full OpenAlex bulk snapshot (~42 min, ~$0.50 on a throwaway us-east-1 EC2 box) and builds `cohort_percentiles` for all 252 subfields (45,857 cohorts, label `openalex-2026-06`), so the observed within-(subfield, year) percentile now covers **every** field, not just the seed. Verified live (e.g. Computer Networks 1998 — a non-seed subfield at a vintage the prior staged rollout never covered — now serves a field percentile). Remaining V1.0: full-corpus synthetic fields, authority-weighting (PageRank), public API.

## 13. Open parameters to settle before building

- Field granularity: settled. The official scoring reference class is the synthetic field, a vintage-matched blend of (subfield, year) cohorts whose weights come from the focal paper's references early (research-front, recency-weighted), migrate to the co-citation community as citations accrue, and, for a brand-new paper with neither references nor citers, fall back to a content-and-authorship prior before ever resorting to OpenAlex's single label (Sections 3 and 5); the OpenAlex Decision Sciences subfields covering the department define the seed calibration cohort (Section 5).
- Vintage window: full year versus narrower (equal-exposure) windows.
- Counting: full versus fractional; exact self-citation rule; authority-weighting scheme and whether it is in the Level 0 MVP or Phase 2.
- The uncited atom: settled. Full-population denominator with the uncited as a tied atom at the mid-rank 100·p₀/2 (§5 denominator rule); revisit only if a small spread proves necessary.
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
- Persson (1994), "The intellectual base and research fronts of JASIS 1986–1990," *JASIS* 45(1):31–38 (research front vs intellectual base).
- Boyack & Klavans (2010), "Co-citation analysis, bibliographic coupling, and direct citation: Which citation approach represents the research front most accurately?" *JASIST* 61(12):2389–2404.
- de Solla Price (1970), "Citation measures of hard science, soft science, technology, and nonscience," in *Communication among Scientists and Engineers* (the Price Index: fraction of references within ~5 years).
- Waltman & Schreiber (2013), "On the calculation of percentile-based bibliometric indicators," *JASIST* 64(2):372–379 (percentiles with large tie mass / uncited).
- Waltman & van Eck (2012), "A new methodology for constructing a publication-level classification system of science," *JASIST* 63(12):2378–2392 (citation-network field delineation).
- Data sources and terms: see data_sourcing.md.
