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
- [ ] **U1 "Working" indicator for slow operations.** Any web action or page load that exceeds ~1s shows a clear working/loading state — a route-transition indicator plus skeleton rows for the explore/author tables and the paper page, and a spinner on the explore fetch (today it only shows a "Loading records…" line; server-rendered pages show nothing during navigation). Goal: the UI never looks frozen.
- [ ] **U2 Dual-metric, sortable columns: show field AND neighborhood QaL side by side.** Compute and store *both* the field-cohort QaL and the co-citation-neighborhood QaL for each paper (extend `compute_qal` + `qal_records` to carry both, not just the official one), and show both as columns in the shared record-list row (and on the paper page). This is the table-level form of §3's required robustness display — agreement signals a robust estimate, divergence flags a field-sensitive one (the Longoni case: field 100 vs neighborhood 68). Requires neighborhoods for the displayed papers (currently the ~325 prefilled set; others show field only until their neighborhood is computed). Supersedes / merges with the M5 robustness-panel item.
  - **No headline toggle needed.** The source of truth / default headline stays the **co-citation neighborhood** (fixed, official — §3, anti-shopping). Exploration is handled entirely by **column sorting**: every column is sortable (the shared `RecordTable` already does this), so a reader who wants to rank by field percentile just clicks that column. Sorting is a pure view operation — it changes the order shown, never the official number that travels with a paper. (This replaces the earlier "headline checkbox" idea.)

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
