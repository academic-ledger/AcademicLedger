# Does the early signal predict eventual quality? An in-field test

*Prepared June 2026. Result for Paper B (the measurement paper). Data: OpenAlex, Management Science and Operations Research (subfield 1803).*

## Design

To approximate the working-paper "early signal" question with data we can actually obtain, we use early citations rather than downloads (the download version needs RePEc/LogEc per-paper monthly series, which is not cleanly accessible; SSRN reports only cumulative totals). Per Karl's refinement, to give every paper a comparable exposure window we restrict to papers with a January 2015 publication date and read citations by calendar year. OpenAlex reports citations in yearly buckets (no citation dates), so the first ~12-month window is "citations dated in calendar 2015." Sample: 4,000 of the ~8,500 January-2015 MS&OR works with a DOI.

## Result

The cohort is heavy-tailed as expected: median 1 eventual citation, mean 8.6, 44% uncited.

The one-year signal is real but modest and bounded. Citations through the end of the first ~12 months rank eventual quality at **Spearman ρ ≈ 0.52**, close to Brody, Harnad and Carr's download-citation r ≈ 0.42 (arXiv physics) and Perneger's hit-citation r ≈ 0.5 (BMJ). At that one-year mark only about **8% of eventual citations have accrued**, the majority of papers are still uncited, and **fewer than half of the eventual top 1% are identifiable**.

The signal sharpens only slowly, which is the decide-late point:

| Years after publication | Rank corr. with eventual (ρ) | Eventual top-1% identified | Eventual citations accrued |
|---|---|---|---|
| 1 | 0.52 | ~45% | 8% |
| 2 | 0.70 | ~57% | 18% |
| 3 | 0.81 | ~68% | 29% |
| 4 | 0.87 | ~75% | 40% |
| 5 | 0.94 | ~82% | 50% |

The rank correlation reaches about 0.9 only after roughly four years, and half of eventual citations have not yet been received even at five years. (The top-1% recall figures are approximate because so many papers are tied near zero early; the rank correlation and the accrued-share columns are robust.)

## Reading

An early observable signal is genuinely informative, enough to rank-order at ρ ≈ 0.5 within a year, but it is far from determinative: most of the eventual quality is literally unrealized at decision time, and the eventual stars are mostly invisible early. This is the same conclusion as the reviewer-prediction result, reached from the opposite direction. Both say: do not commit a final verdict at submission; admit broadly and let quality reveal itself. It is the empirical case for deciding late.

## Caveats

- Citation signal, not downloads. The download version (Brody's exact design) requires RePEc/LogEc per-paper monthly data we would obtain separately.
- OpenAlex publication dates often reflect the issue date, and January is inflated by volume-start stamping, so the January cohort is large and some papers may have appeared later in the year. That adds noise to the exposure window and, if anything, attenuates the one-year correlation, so ρ ≈ 0.52 is a conservative floor.
- Yearly citation buckets only; "12 months" means citations dated in the publication calendar year.
- One field (MS&OR), one cohort year; worth replicating in economics and across cohort years.
- Sample of 4,000; correlations are stable at this size.

## Reproducibility

Pull and analysis scripts and the cohort sample are saved alongside the figure: `webapp/images/fig_early_signal.py`, `cohort_jan2015.json`, `jan_horizon.json`. Source: OpenAlex API, subfield 1803, January 2015, has_doi:true.

*Verified reference for comparison: Brody, T., Harnad, S., & Carr, L. (2006). Earlier Web Usage Statistics as Predictors of Later Citation Impact. JASIST 57(8):1060–1072. Perneger, T. V. (2004). BMJ 329:546–547.*
