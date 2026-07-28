# Do early downloads predict eventual citations? — the preprint pilot

*Result for Paper B (Result 2), July 2026. A pilot for the economics download-to-citation study,
run on preprint servers because they expose open per-article download data. Every number is real.*

## Why this pilot

Paper B's Result 2 asks whether **early download activity predicts eventual citations** for working
papers — an *even earlier* signal than early citations, observable months before any citation can
accrue. The classic out-of-field benchmarks are Brody, Harnad & Carr (2006), arXiv physics
(download→citation *r* ≈ 0.4) and Perneger (2004), BMJ medicine (*r* ≈ 0.5, plateauing by ~6 months).

The **economics** version (a 2015 RePEc working-paper cohort, downloads from LogEc) is currently
**blocked on data access**: LogEc's per-item download pages sit under `/scripts/`, which LogEc's
`robots.txt` disallows, so the counts must be **requested** from the RePEc maintainers, not scraped
(the same terms-first posture that keeps SSRN off-limits — see `data_sourcing.md`). That request is
pending.

This pilot runs the **identical pipeline** on the two preprint servers that *do* publish open
per-article download data, to (a) validate the method end-to-end before the economics data arrives
and (b) put an in-domain benchmark in hand.

## Design

- **Cohorts** (matured, with full early-download histories):
  - **medRxiv 2019** (medicine), **N = 913** — pre-COVID, the server's first cohort, fully matured.
  - **bioRxiv 2017** (biology), **N = 2,484** — a deterministic ~22% hash sample of the 11,340-paper
    cohort; larger and longer-matured, as a robustness check.
- **Early downloads**: per-article **monthly PDF downloads** from the open **Rxivist** database dump
  (Zenodo `10.5281/zenodo.7688682`; crawl frozen 2023-02, so the first-12-month window is fully
  captured for both cohorts). We cumulate downloads over the first **1, 3, 6, and 12 months** from
  posting.
- **Eventual citations**: from **OpenAlex**, joined by DOI (`10.1101/…`); 100% of the sampled DOIs
  matched. We use total citations to date (and a 5-year-window variant, which gives the same ranks).
- **Statistic**: Spearman ρ between early downloads and eventual citations at each window (the
  "plateau" curve), plus the atom-robust **AUC** for identifying the eventual top decile from
  6-month downloads.

## Result

| Cohort | N | ρ @1mo | ρ @3mo | ρ @6mo | ρ @12mo | AUC (top decile, dl@6mo) |
|---|---:|---:|---:|---:|---:|---:|
| medRxiv 2019 · medicine | 913 | 0.23 | 0.35 | 0.35 | 0.36 | 0.76 |
| bioRxiv 2017 · biology | 2,484 | 0.37 | 0.42 | 0.45 | 0.47 | 0.78 |

*Benchmarks: Brody et al. (arXiv physics) r ≈ 0.4; Perneger (BMJ medicine) r ≈ 0.5; both plateau by
~6 months.* See `analysis/download_citation_pilot/fig_download_citation.png`.

## Reading

- **Early downloads predict eventual citations at ρ ≈ 0.35 (medicine) to 0.47 (biology)** — squarely
  in the Brody/Perneger band, now shown in-domain for preprint servers with modern data.
- **The signal plateaus fast** — by ~3 months (medRxiv) to ~6 months (bioRxiv), reproducing
  Perneger's central finding. Waiting past the first months buys almost nothing in *download* signal.
- Downloads are a **dense** signal: **every paper has downloads** (0% zero), unlike citations
  (24–29% uncited even years later), and they are observable in the very first month — the earliest
  ex-post signal we have.
- The signal is **real but bounded** (ρ ≈ 0.4, AUC ≈ 0.77): early attention rank-orders eventual
  impact meaningfully but is far from determinative — the eventual stars are not cleanly separable
  early. This is the same conclusion as the citation-based early-signal study (ρ ≈ 0.52 at one year on
  the MS&OR cohort), reached from an *even earlier* vantage point. It is direct support for **"admit
  broadly, decide late"** — and it depends on no assumption about AI evaluators.

## Caveats (these estimates are conservative)

- **Version attribution attenuates the correlation.** OpenAlex citations here are to the *preprint*
  DOI; when a preprint is published in a journal, citations partly accrue to the *published* version
  (a separate record), which we do not add in. Because being downloaded and being published are
  positively related, this undercount likely **attenuates** the true download→impact correlation —
  the real numbers are probably somewhat higher. (A refinement using Rxivist's `article_publications`
  → published-DOI citations is a natural robustness check.)
- **medRxiv 2019 is a young, small, possibly atypical cohort** (the server launched mid-2019;
  early adopters), which may explain its lower ρ than bioRxiv.
- **This is preprints, not working papers.** Download and citation cultures differ between bioRxiv/
  medRxiv and economics WPs, so the pilot validates the *method* and benchmarks the *effect size
  range*; it does not substitute for the economics number, which the RePEc request will produce.
- bioRxiv here is a ~22% sample; medRxiv is the full 2019 cohort.

## Relation to the economics study

Same estimand, same pipeline (early usage → eventual citations; Spearman + AUC + the plateau curve).
When the RePEc/LogEc download data arrives for the 2015 economics cohort, the eventual-citation side
is already built (OpenAlex, join by handle/DOI) and this analysis code applies directly. The pilot
de-risks the machinery and anchors the expected effect size (ρ ≈ 0.35–0.47, plateauing by ~6 months).

## Reproducibility

`analysis/download_citation_pilot/`: `extract_downloads.py` (Rxivist dump → per-article early
downloads), `analyze.py` (merge with OpenAlex citations → correlations + figure), the cached
`rxiv_cohort_merged.json`, `results.json`, and `fig_download_citation.png`.

**Data.** Rxivist dump: Abdill & Blekhman, Zenodo `10.5281/zenodo.7688682` (CC dataset), crawl frozen
2023-02. Citations: OpenAlex (CC0), July 2026.

**Verified references.** Brody, T., Harnad, S., & Carr, L. (2006). Earlier web usage statistics as
predictors of later citation impact. *JASIST* 57(8), 1060–1072. Perneger, T. V. (2004). Relation
between online "hit counts" and subsequent citations. *BMJ* 329, 546–547. Abdill, R. J., & Blekhman,
R. (2019). Tracking the popularity and outcomes of all bioRxiv preprints. *eLife* 8, e45133.
