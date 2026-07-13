# CLAUDE.md — academic Ledger / QaL

Operating manual for this repo. Read this first.

## What this is
academic Ledger (aL) reframes academic publishing by separating **distribution** (already solved) from **certification** (the hard part). It replaces the binary accept/reject verdict with **QaL** (said "qual"): a calibrated, continuously updated estimate of a paper's eventual standing in its field, reported as a percentile with an honest interval. Production domain: **academic-ledger.org**. Initiated by Gérard Cachon, Christian Terwiesch, and Karl Ulrich (Wharton OID).

## Sources of truth (do not contradict these; update them if a decision changes)
- `docs/QaL_spec.md` — THE PRD. The estimand, reference class, estimator, data sources, architecture, the three versions (POC/MVP/V1.0), and acceptance criteria.
- `web/` (the live Next.js app, deployed at academic-ledger.org) — **the UI source of truth.** The pages have been built and have moved past the early mocks; design from the live pages, not the mocks. `docs/mocks/` (`paper-mvp.html`, etc.) is a **frozen historical design reference only** — do not port from it or sync it.
- `docs/data_sourcing.md` — the open data spine and the terms-of-use boundary (notably: do NOT scrape SSRN).
- `web/API_CONTRACT.md` — the read-API shape the web app consumes.

## Architecture (internalize this split)
Four pieces. **Vercel never does heavy compute.**
- **GitHub** — repo + Actions. The *light* batch (seed-cohort calibration, the synthetic-field worker, coverage rollout) runs here on cron. Actions can't do the *full-corpus* scan: 6h job cap + cross-cloud transfer from the AWS-hosted OpenAlex S3.
- **AWS EC2 (us-east-1), on demand** — the *heavy* batch. `pipeline/factory.py` scans the full OpenAlex bulk snapshot in one in-region DuckDB pass (~1h, ~$0.50) and writes comprehensive `cohort_percentiles` to Neon. Launched and torn down by `pipeline/factory_launch.py` — a throwaway self-terminating box, no SSH (this network blocks outbound 22 *and* 5432; it reports via the serial console). See the academic-ledger-aws-factory memory.
- **Vercel** — the Next.js web app and a light read-only API. It reads precomputed tables and serves pages. Custom domain academic-ledger.org.
- **Neon (managed Postgres)** — the data layer (`db/schema.sql`). The pipeline (Actions + the EC2 factory) writes it; Vercel reads it.

Cheap things can run on the fly (work fetch, exact within-cohort percentile via two count queries, calibration-table lookup, retraction flag). Graph things (co-citation neighborhood / RCR, PageRank) must be precomputed in batch and cached. See QaL_spec.md §11.

## Stack
- `web/` — Next.js (App Router, TypeScript). Route handlers under `app/api/*` implement `web/API_CONTRACT.md`. Port the mocks; keep them responsive and mobile-friendly (QaL_spec.md interface requirements: single column below ~700px, wide tables scroll within their container, renders at ~380px).
- `pipeline/` — Python batch jobs. Seed/calibrated path: `pull_cohort.py` → `build_percentiles.py` → `calibrate.py` → `compute_qal.py` (config in `pipeline/cohorts.yml`). For the **full-corpus universal layer**, `factory.py` supersedes `pull_cohort.py`+`build_percentiles.py` — it builds `cohort_percentiles` for *every* subfield straight from the bulk snapshot (in-region, no API); `calibrate.py`/`compute_qal.py` still run for the Layer-B seed.
- `db/schema.sql` — Postgres DDL: `works`, `cohort_percentiles`, `calibration_models`, `qal_records`, `authors`.

## Product decisions already made (honor unless told otherwise)
- **QaL is the calibrated posterior over eventual percentile**, not a transform of current citations. Report point + 90% interval + NSF-bucket probabilities. (§2)
- **Official reference class = the co-citation neighborhood** (RCR), because it is robust to OpenAlex single-field misclassification. Field percentiles are an exploration view only; the official number is fixed (no reference-class shopping). (§3)
- **Two layers.** The universal layer (metadata, observed within-(subfield,year) percentile, retraction, links, neighborhood context) works for ANY paper. The calibrated posterior is scope-bound. (§1, §5)
- **Calibration seed = the Decision Sciences subfields covering the OID department: 1803 (Mgmt Sci & OR), 1802 (Info Systems & Mgmt), 1800 (General Decision Sciences).** Optional cheap extensions: 1405, 1804. Papers outside the seed are scored universally but shown **calibration-pending**. (§5, `pipeline/cohorts.yml`)
- **No single author-level score.** The author page shows a per-paper distribution, never a scalar. (mock rationale)
- **Everything is illustrative pending calibration** until the Layer-B back-test passes; label it so. (§10)

## Commands
```bash
# pipeline (needs DATABASE_URL + OPENALEX_MAILTO; see .env.example)
pip install -r pipeline/requirements.txt
python pipeline/pull_cohort.py --config pipeline/cohorts.yml
python pipeline/build_percentiles.py
python pipeline/calibrate.py
python pipeline/compute_qal.py            # P5: still a stub — implement the join

# web
cd web && npm install && npm run dev      # P? after create-next-app
```

## Current state
- Built: the four mocks + real data files; the Python pipeline skeletons (pull/percentile/calibrate run against live OpenAlex; smoke-tested); `db/schema.sql`; the CI cron; the read-API contract.
- Stubbed / TODO: `pipeline/compute_qal.py` (the join to `qal_records`); the calibration back-test/validation; the Next.js app itself (run `create-next-app` in `web/`, then port the mocks and implement the API routes).

## Conventions / standards
- The principals hold a high evidence bar. **Any reference or citation that appears in docs or on the site must be verified, never invented.** When unsure, omit.
- Secrets never get committed. `DATABASE_URL` and `OPENALEX_MAILTO` live in Vercel env and GitHub Actions secrets. `.env` is gitignored.
- Be a good OpenAlex citizen: send the polite-pool `mailto`, page with cursors, cache, refresh monthly.

## Working together (multiple authors, each with their own Claude Code)
Collaboration happens entirely through this GitHub repo — not through shared Claude sessions. This file and `docs/` are the shared context every collaborator's Claude reads on startup, so **decisions live here, not in any one person's private notes.**
- **Onboarding a new machine:** clone; `cp .env.example .env` and fill your **own** credentials (get your own Neon + Vercel access rather than copying someone else's); `pip install -r pipeline/requirements.txt`; `cd web && npm install`; then run the hook-activation command below.
- **Activate the shared git hooks (once per clone):** `git config core.hooksPath githooks`. This wires up `githooks/pre-commit`, which regenerates `web/public/talk.html` whenever `docs/talk/master_presentation.md` is committed. Without it, the hosted deck silently goes stale.
- **`main` auto-deploys to Vercel.** Never push straight to `main`. Work on a feature branch, open a PR, and get a review before merging. Keep PRs small and frequent to avoid merge pain and to give each other (and each Claude) a real review checkpoint.
- **Pull before you start**, and coordinate who owns which surface (deck / pipeline / web) so two agents don't edit the same files at once.
- **Secrets never touch git or chat.** The only GitHub-resident secrets are the two Actions secrets `DATABASE_URL` and `OPENALEX_MAILTO`; everything else lives in Vercel/Neon. See `.env.example`.

## First milestone
See `BUILD_BACKLOG.md` (the POC checklist). POC = the paper/author/explore/about pages live as a Next.js app on academic-ledger.org, reading real observed percentiles for the seed fields, with QaL shown illustratively and calibration-pending handled honestly.
