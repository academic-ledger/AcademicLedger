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

- [ ] **M1 Datastore.** Provision Neon; run `db/schema.sql`.
- [ ] **M2 Ingest.** `pull_cohort.py` over the seed subfields (1803/1802/1800) for score years + historical calibration years (`cohorts.yml`).
- [ ] **M3 Percentile tables.** `build_percentiles.py` → `cohort_percentiles` (O(1) lookups).
- [ ] **M4 Calibrate Layer B.** `calibrate.py` on the mature historical cohorts; **then back-test that the 90% interval covers ~90%** (QaL_spec.md §10 acceptance). This is the gate.
- [ ] **M5 Co-citation neighborhood (RCR).** Batch-assemble each seed paper's neighborhood; this becomes the official reference class.
- [ ] **M6 Compose + serve.** Implement `compute_qal.py` (the join to `qal_records`); switch the API to read-through cache; monthly cron via `.github/workflows/refresh.yml`.
- [ ] **M7 Retraction overlay** (Retraction Watch via Crossref) and the Zenodo "deposit a new record" affordance.
- [ ] **M8 Make the paper page parameter-aware** so `paper/:id` loads the clicked work (closes the author→paper click-through).

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
