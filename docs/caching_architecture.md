# Decision note — caching vs. live retrieval (what to persist)

**Status:** decision note. Question: do we keep a local snapshot of the whole corpus, or
just cache what's expensive to derive and fetch the rest live?

## Frame

Separate two things we've been conflating:
- **The cache we want** — computed artifacts that are expensive or impossible to derive on a
  page view: the QaL records, the field distributions, the calibration fit, the synthetic
  field. Caching these is good-citizen (fewer OpenAlex hits) and good UX (fast serves). §11
  prescribes exactly this: "store the final QaL record per Work ID; serve read-through;
  refresh monthly."
- **The raw corpus we accidentally persist** — the ~371k raw `works` rows. This is not an
  asset; it's a *transient input* to (1) building the distributions, (2) the calibration fit,
  (3) the explore leaderboard display + the paper-page fallback. It is also the source of the
  staleness we keep fixing (the explore table still shows frozen bylines from `works`).

The paper page already constructs live (single-entity OpenAlex fetch + cached QaL), so the
display-truth question is settled for the detail view. This note is about the **store**.

## Sub-decisions where the answer is clear (recommendation, not a fork)

| Question | Recommendation | Why |
|---|---|---|
| Persist the raw `works` table? | **No** — retire it. | It's an intermediate. Drop it once its display fields move into the cache. Kills the last stale-snapshot surface (explore). |
| Where do display fields (title, byline, venue) live? | **In `qal_records`** (the cache). | Then explore + the paper-page fallback read the cache, not a raw snapshot; nothing to keep stale. |
| How are field distributions built without stored works? | **Stream the cohort at refresh**, reduce to the CDF, discard the works. | `cohort_percentiles` is the persistent artifact; the works behind it are transient. Monthly batch cost only. |
| Calibration fit inputs (historical `counts_by_year`)? | **Pull at fit-time, discard.** | Re-fit is occasional; no need to persist 200k historical works between fits. |
| Distributions / calibration / synthetic field / subfields? | **Keep** (they're the small, expensive caches). | This is the legitimate precompute §11 wants. |

## The one genuine fork: **how much of the corpus to keep pre-scored**

The explore leaderboards rank by QaL. To rank, papers must be scored. The question is whether
we eagerly score-and-cache the **whole seed corpus** or only the **leaderboard-relevant slice**.

**Option A — Eager-cache the full seed corpus (~372k in `qal_records`).**
- Pro: simplest model; leaderboards are complete down the tail; any seed paper serves instantly.
- Con: the monthly refresh recomputes ~372k rows; the cache is large (storage is fine
  post-upgrade, so this is mostly refresh-compute cost, not space).

**Option B — Eager-cache only the leaderboard slice + read-through the tail.**
- Eagerly score the papers anyone actually ranks/opens: the calibrated seed papers, each
  community's top-by-citation slice, author/displayed papers, everything with a synthetic
  field (~tens of thousands). The deep low-QaL tail is *not* pre-scored; opening such a paper
  computes it on the fly and caches it (read-through, TTL).
- Pro: bounded cache; lighter monthly refresh; closest to §11's "recompute on a miss"; the
  on-the-fly path already exists, so the tail is free to serve.
- Con: more moving parts (a write-through path + TTL); the leaderboard ranks "the top," not
  the deep tail (which no one views — QaL≈citation-rank, so the top is the highly-cited slice).

**Recommendation: A now, with the door open to B.** Storage is no longer the constraint, and
eager-scoring the seed is the simplest thing that gives complete leaderboards; the on-the-fly
path *already* covers any non-seed / arbitrary paper as read-through. If the monthly refresh
of ~372k rows ever becomes the bottleneck, trim to B (the leaderboard slice) — but that's a
performance optimization to make when it bites, not a day-one necessity.

## Target architecture (under the recommendation)

- **Live:** single-entity OpenAlex fetch for the paper-page display (done).
- **Persistent caches:** `qal_records` (computed QaL **+ folded-in display fields**, the
  read-through cache), `cohort_percentiles`, `calibration_models`, `synthetic_field`,
  `subfields`, `authors`/`author_works`.
- **Retired:** the raw `works` table. Distributions rebuilt by streaming cohorts at the
  monthly refresh; calibration cohorts pulled transiently at fit-time.
- **Refresh:** the monthly cron (M6) recomputes distributions → calibration → `qal_records`
  for the seed and refreshes the synthetic field for the leaderboard set; on-demand entries
  carry a ~monthly TTL.

## Migration (deliberate, sequenced)

1. Add `title`/`authors`/`venue` to `qal_records`; populate from current `works`.
2. Point explore (`getExplore`) and the paper-page fallback at `qal_records` display fields.
3. Move `cohort_percentiles` rebuild to a streaming pass (no persisted works); make calibrate
   pull its cohorts transiently.
4. Drop the `works` table.
5. Fold all of the above into the M6 monthly cron.
