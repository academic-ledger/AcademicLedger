# Build backlog

Milestones map to QaL_spec.md §12 (POC / MVP / V1.0). Check items off as you go.

## POC — pages live, real observed percentiles, QaL illustrative  ✅ complete
- [x] **P1 Scaffold the web app.** Next.js (App Router, TypeScript) in `web/`; shared brand bar + nav; responsive to ~380px.
- [x] **P2 Port the mocks** into components/pages; one shared record-list component (`RecordTable`) across explore + author.
- [x] **P3 Read API** (`app/api/*`) per `API_CONTRACT.md`: `/api/qal/:oaid`, `/api/author/:oaid`, `/api/explore` — reads Neon.
- [x] **P4 Calibration-pending UX** — papers outside the calibrated communities show observed standing only, labeled honestly.
- [x] **P5 Deploy** — Vercel + custom domain (apex `academic-ledger.org` → `www`); renders on desktop and phone width.

## MVP — real headline metric for the seed, cached
- [x] **M1 Datastore.** Neon + `db/schema.sql` (`works`, `cohort_percentiles`, `calibration_models`, `qal_records`, `authors`, `author_works`, `synthetic_field`, `subfields`).
- [x] **M2 Ingest.** `pull_cohort.py`: **1800** full (~32k); **1803 & 1802** as 10k/cohort uniform random samples (full subfields are ~716k/~526k). `--sample` + batched upserts.
- [x] **M3 Percentile tables.** `build_percentiles.py` → `cohort_percentiles`, full-population **mid-rank** convention; min-cohort-size guard.
- [x] **M4 Calibrate Layer B.** `calibrate.py` pools vintages + per-age **split-conformal** widening (`calib_lib.py`). **Back-test passes** (`backtest.py`): ~0.90–0.91 leave-one-vintage-out coverage across 1803/1802/1800 (raw ~0.80 was overconfident; conformal fixed it).
- [x] **M5 Official reference class = the synthetic field.** `synthetic_field.py` (QaL_spec §3/§5): per paper, staged topic-mixture weights — reference-based recency stage (research front) migrating to the co-citation community as citations accrue (λ = c/(c+k)) — then rank the paper against the **full-population blend** of those (subfield, vintage) cohorts via **exact count queries** (uncited atom at mid-rank 100·p₀/2). The earlier cited-only co-citation-*neighborhood* ranking was a flaw (it put a top paper at the ~22nd percentile) and has been **deleted** — nothing ranks against a cited-only/popularity-biased set. Regression test `pipeline/test_percentile.py` pins the rule. Prefilled the top ~480 seed/leaderboard papers (cached; serving reads it).
- [~] **M6 Compose + serve.** `compute_qal.py` joins works + `cohort_percentiles` + `calibration_models` + `synthetic_field` → `qal_records` (carries **both** field and synthetic metrics); API reads through from Neon. **Still to do: wire the monthly cron** (`.github/workflows/refresh.yml`) to run pull → percentile → calibrate → compute (+ synthetic). *(A launchd one-shot currently resumes the synthetic prefill after the daily OpenAlex quota resets — a stopgap, not the cron.)*
- [ ] **M7 Retraction overlay** (Retraction Watch via Crossref) + the Zenodo "deposit a record" affordance.
- [x] **M8 Paper page parameter-aware** — `paper/[oaid]` loads the clicked work.
- [ ] **M9 Author ingest — make the author page work for any author.** The page is already a generic template (`author/[oaid]` + `getAuthor`), but `authors`/`author_works` hold one seeded author (Ulrich). Build `pipeline/author_ingest.py` (author analog of `pull_cohort.py`): given an OpenAlex author id / ORCID, pull the author entity into `authors`, populate `author_works`, and upsert their works into `works`/`qal_records` (QaL where in a calibrated seed community; universal/pending otherwise). Caveat: arbitrary authors span subfields we haven't pulled, so it's fully meaningful only for authors largely inside the seed communities until the V1.0 store. Keep the no-single-author-score rule.

## Display & UX
- [x] **U1 "Working" indicator.** Route `loading.tsx` skeletons + top route-transition bar; explore fetch shows a skeleton table + spinner; shimmer honors `prefers-reduced-motion`.
- [x] **U2 Dual-metric, sortable columns.** `qal_records.metrics` carries both; the shared table shows **`QaL · field`** and **`QaL · synthetic ★`** as sortable columns (official highlighted, "—" where not yet computed). No headline toggle — **column sorting** is the exploration affordance; the official number stays the synthetic field (§3, anti-shopping). *(Explore search/filter now run server-side over the full DB, not a pre-fetched slice.)*
- [x] **U3 Synthetic-field composition on the paper record.** Ranked subfield-weight bars from `synthetic_field.weights`, showing the paper's true intellectual blend vs OpenAlex's single label ("divergence is the signal"). Names come from the dynamic `subfields` table; `pipeline/fetch_subfields.py` completes the ~250-name taxonomy (wired into the scheduled backfill, so remaining names auto-fill — no redeploy).
- [x] **U4 Full citation on the paper page.** Formatted reference (authors · year · title · venue · DOI) + copy button. **Enrichment TODO:** volume/issue/pages from OpenAlex `biblio` (capture in `pull_cohort._row` + backfill); optional BibTeX/RIS export.
- [ ] **U5 Drop the Access cell.** Remove the OA-status (Open/Closed) cell from the paper-page evidence grid (`page.tsx`): `oa_status` is Unpaywall's open-access classification, not a reader-useful fact, and it understates real availability (e.g. W2103157313 has submitted-version drafts in ScholarlyCommons/RePEc yet reads "Closed"). Keep `is_oa`/`oa_url` in the data layer (optional later: a "free copy" link in Read & cite only when `oa_url` is non-null). Reserve the freed 3×2 grid slot for a future signal; Read & cite already provides access paths.
- [ ] **U6 Composition as a flat strip (no graphic).** Replace the "Reference-class composition" card (the ranked subfield bars, `.comp`/`.comptrack`/`.compfill`) with a compact full-width strip placed directly under the QaL hero, above the Evidence card. No bars: a short label ("Synthetic field · weighted by recent references") followed by a flat list of the contributing subfields ordered by descending fraction, each as "Subfield name (NN%)", separated by middots; collapse a long tail into "+N more (X%)". Keep the divergence-from-OpenAlex note.

- [ ] **U7 About: transparency note + links (repo + white paper).** Add a short note to the About page along the lines of: *"academic Ledger is an independent, not-for-profit initiative built on principles of transparency. The full codebase and documentation are at [our git repository], and a white paper describing the methodology is [here]."* Links: the GitHub repo (`https://github.com/ktulrich/AcademicLedger`) and the methodology white paper. **Dependency:** the white paper is currently `docs/QaL_whitepaper.md` (markdown) — to link to a white-paper *HTML* we need to render it and serve it (e.g. `web/public/whitepaper.html`, the way `talk.html` is served), or publish it elsewhere and link out. Finalize the exact wording with the principals (and the not-for-profit phrasing — confirm legal status).

## V1.0 — the Lens at scale
- [ ] Ingest the OpenAlex bulk snapshot into the owned store — drops the live-API dependency and its **daily quota**, which currently bounds the per-paper synthetic-field prefill.
- [ ] Full-corpus cohort tables, synthetic fields, and authority-weighting (PageRank).
- [ ] Public read API; QaL-ranked leaderboards as a public good; calibrate more communities (e.g. Applied/Social Psychology, a computational-social-science bundle).
- [ ] Coverage limits (law, humanities) reported honestly; manipulation-robustness audited.

## Decisions log (so they are not relitigated)
- **Official reference class = the synthetic field** — a recency-weighted topic-mixture blend of full (subfield, vintage) cohorts (reference-based → community migration). The cited-only co-citation *neighborhood* is **not** a ranking cohort (it's popularity-biased and has no uncited papers); it only informs the topic mixture. (QaL_spec §3/§5.)
- **Denominator rule:** every percentile is over the **full population** (cited + uncited), never cited-only and never a top-N/sorted sample; the uncited atom takes the **mid-rank 100·p₀/2**; the same convention is used for r_obs and r∞.
- Calibration seed = Decision Sciences subfields **1803, 1802, 1800** (extensions 1405, 1804 available).
- QaL = calibrated posterior over eventual percentile (point + 90% interval + bucket probs); back-tested to ~90% coverage via per-age split-conformal.
- **No single author-level score** (author page shows a per-paper distribution).
- Stack = GitHub (batch) + Vercel/Next.js (web + read API) + Neon Postgres; **Vercel does no heavy compute**.
