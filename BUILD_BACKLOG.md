# Build backlog

Milestones map to QaL_spec.md §12 (POC / MVP / V1.0). Check items off as you go.

## POC — the pages live, real observed percentiles, QaL illustrative
Goal: paper / author / explore / about as a Next.js app on academic-ledger.org, reading real within-(subfield,year) percentiles for the seed fields, QaL shown illustratively, calibration-pending handled honestly. No heavy graph compute yet.

- [ ] **P1 Scaffold the web app.** `create-next-app` (TypeScript, App Router) in `web/`. Wire the shared brand bar + nav (Explore, Author, About, Talk). Carry the responsive rules from the mocks (mobile-friendly, ~380px).
- [ ] **P2 Port the mocks** into components/pages: `app/page.tsx` (explore), `app/author/[id]/page.tsx`, `app/paper/[id]/page.tsx`, `app/about/page.tsx`. Reuse one shared record-list component across explore and author.
- [ ] **P3 Read API** (`app/api/*` route handlers) per `web/API_CONTRACT.md`: `/api/qal/:oaid`, `/api/author/:oaid`, `/api/explore`. For POC these may call OpenAlex live and compute the observed percentile with two count queries; no DB required yet.
- [ ] **P4 Calibration-pending UX.** A paper outside the seed subfields shows observed standing + a calibration-pending tag (no QaL interval). Mirror the mock behavior exactly.
- [ ] **P5 Deploy.** Vercel project + custom domain academic-ledger.org; verify it renders on desktop and a phone-width viewport.

## MVP — real headline metric for the seed, cached
Goal: the real co-citation-neighborhood headline and a back-tested calibrated posterior for the seed communities, served from Postgres.

- [x] **M1 Datastore.** Neon provisioned; `db/schema.sql` applied (+ `author_works`, `authors.seed`).
- [x] **M2 Ingest.** All three seed communities: **1800** full (~31.9k), **1803 & 1802** as 10k/cohort uniform random samples (full subfields are ~716k/~526k — too big for the free tier; sample is statistically sufficient). `pull_cohort.py --sample`.
- [x] **M3 Percentile tables.** `build_percentiles.py` → `cohort_percentiles` for all pulled cohorts (min-cohort-size guard).
- [x] **M4 Calibrate Layer B.** `calibrate.py` pools across vintages + per-age split-conformal widening (`calib_lib.py`). **Back-test PASSES for all three communities** (`backtest.py`): overall coverage **0.911** (1803 0.923, 1802 0.903, 1800 0.886) over 1.76M LOVO test points. Raw was ~0.80 (overconfident); conformal fixed it.
- [x] **M5 Co-citation neighborhood (RCR).** `pipeline/neighborhood.py` assembles each paper's co-citation neighborhood (citers → reference lists, Hutchins 2016) and caches it (`neighborhoods` table); it is the **official** reference class when present (else field stand-in). Prefilled seed-author + top-100/community leaderboard papers (~325). `compute_qal` serves the neighborhood percentile as the official standing (calibration-pending for non-seed communities). Robustness panel (all-fields/per-field side-by-side) still to add to the paper page.
- [~] **M6 Compose + serve.** `compute_qal.py` implemented (the join to `qal_records`); API already read-through from Neon. **Still: monthly cron wiring (`.github/workflows/refresh.yml`) to call pull→percentile→calibrate→compute.**
- [ ] **M7 Retraction overlay** (Retraction Watch via Crossref) and the Zenodo "deposit a new record" affordance.
- [x] **M8 Paper page is parameter-aware** — `paper/[oaid]` loads the clicked work (done in the POC scaffold).

## Display & UX backlog
- [x] **U1 "Working" indicator for slow operations.** Done — route `loading.tsx` for paper/author/explore stream a skeleton (brand bar + shimmer hero/table) and a top route-transition bar while the server pages fetch from Neon; the explore client fetch shows a skeleton table + inline spinner. `components/Skeleton.tsx`; shimmer honors `prefers-reduced-motion`. The UI no longer looks frozen during navigation or data loads.
- [x] **U2 Dual-metric, sortable columns: show field AND neighborhood QaL side by side.** Done — `qal_records.metrics` carries both; the shared table shows `QaL · field` and `QaL · neighborhood ★` as sortable columns (official highlighted, "—" where a class doesn't apply). Follow-ups: show both numbers on the paper page hero too; author-page portfolio distribution still keys off the official obs. **Storage note:** this hit Neon's 512MB free tier — fixed by trimming stored metrics + TRUNCATE/rebuild to shed re-run bloat (DB ~373MB). The free tier is now ~70% full; expanding the seed or storing more works will require a paid Neon plan. Compute and store *both* the field-cohort QaL and the co-citation-neighborhood QaL for each paper (extend `compute_qal` + `qal_records` to carry both, not just the official one), and show both as columns in the shared record-list row (and on the paper page). This is the table-level form of §3's required robustness display — agreement signals a robust estimate, divergence flags a field-sensitive one (the Longoni case: field 100 vs neighborhood 68). Requires neighborhoods for the displayed papers (currently the ~325 prefilled set; others show field only until their neighborhood is computed). Supersedes / merges with the M5 robustness-panel item.
  - **No headline toggle needed.** The source of truth / default headline stays the **co-citation neighborhood** (fixed, official — §3, anti-shopping). Exploration is handled entirely by **column sorting**: every column is sortable (the shared `RecordTable` already does this), so a reader who wants to rank by field percentile just clicks that column. Sorting is a pure view operation — it changes the order shown, never the official number that travels with a paper. (This replaces the earlier "headline checkbox" idea.)
- [ ] **U3 Show the synthetic-field composition on the paper record.** Surface the "top synthetic subfields with fractions" — the recency-weighted topic-mixture `weights` already stored in `synthetic_field.weights` — on the paper page. It makes the misclassification-robustness story visible: the reader sees the paper's *true* intellectual community as a weighted blend (e.g. the LLM-ideation paper: Cognitive Psychology .21, AI .17, Sociology/PoliSci .11, Health Informatics .10, CS Apps .05…) rather than OpenAlex's single label. Render as a small ranked bar/chip list under the QaL hero or in an "Reference class composition" card; the divergence between the single field label and this blend is itself the signal. Implementation: flow `weights` through `getQalRecord` (it's already in the DB); needs a subfield-id→label map (have the seed labels in `cohorts.yml`; fetch/cache the rest from OpenAlex, or ship a static OpenAlex subfield-name table). Pairs naturally with the §3 robustness panel.

## V1.0 — the Lens at scale
- [ ] Ingest the OpenAlex bulk snapshot into the owned store (drop live-API dependency).
- [ ] Full-corpus cohort tables, neighborhoods, and authority-weighting (PageRank).
- [ ] Public read API; QaL-ranked leaderboards as a public good; calibration across more communities (expand the seed; consider Applied/Social Psychology and a computational-social-science bundle to cover the wider department).
- [ ] Coverage limits (law, humanities) reported honestly; manipulation-robustness audited.

## Decisions log (so they are not relitigated)
- Official reference class = co-citation neighborhood; field percentiles are exploration only.
- Calibration seed = Decision Sciences subfields 1803, 1802, 1800 (extensions 1405, 1804 available).
- QaL = calibrated posterior over eventual percentile (point + 90% interval + bucket probs).
- No single author-level score.
- Stack = GitHub (batch) + Vercel/Next.js (web + read API) + Neon Postgres; Vercel does no heavy compute.
