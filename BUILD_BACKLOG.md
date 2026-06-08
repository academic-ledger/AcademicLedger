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
- [~] **M2 Ingest.** `pull_cohort.py` run for **1800** (General Decision Sciences, ~31.9k works, score + calibration years). **1803 and 1802 still to pull** (larger; same code, `--subfields`).
- [x] **M3 Percentile tables.** `build_percentiles.py` → `cohort_percentiles` for the 17 pulled 1800 cohorts (min-cohort-size guard added).
- [x] **M4 Calibrate Layer B.** `calibrate.py` pools across vintages + applies per-age split-conformal widening (`calib_lib.py`). **Back-test PASSES** for 1800: leave-one-vintage-out coverage 0.886 (raw was 0.80 — overconfident; conformal fixed it). `backtest.py` is the gate.
- [ ] **M5 Co-citation neighborhood (RCR).** Batch-assemble each seed paper's neighborhood; this becomes the official reference class.
- [~] **M6 Compose + serve.** `compute_qal.py` implemented (the join to `qal_records`); API already read-through from Neon. **Still: monthly cron wiring (`.github/workflows/refresh.yml`) to call pull→percentile→calibrate→compute.**
- [ ] **M7 Retraction overlay** (Retraction Watch via Crossref) and the Zenodo "deposit a new record" affordance.
- [x] **M8 Paper page is parameter-aware** — `paper/[oaid]` loads the clicked work (done in the POC scaffold).

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
