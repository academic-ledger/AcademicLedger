# Design note — paper page construction: on-the-fly / read-through

**Status:** implemented. Updated 2026-06-18 for the V1.0 factory (universal cohort lookup) and the
synthetic-compute behavior gate.
**Motivation:** the paper page currently renders display fields (title, authors, venue,
citations, OA, retraction) from the *stored* `works` snapshot. Snapshots go stale — e.g.
W1562368000 shows "Reid Hastie et al." when the work has exactly two authors, because it was
pulled before the §12 all-co-authors rule and wasn't in the set we backfilled. ~204k of 371k
stored works carry the old byline format. Storing a per-paper snapshot for *display* is the
avoidable part; the spec (§11) prescribes the cheap path on the fly.

## Principle (QaL_spec §11)

- **Cheap, on the fly:** fetch the work record (one OpenAlex call), compute the field
  percentile (two count queries or an O(1) cohort-table lookup), read the calibration table,
  read the retraction flag. The paper page is allowed to do this — it is *not* graph compute.
- **Must be precomputed/cached (preferred):** the synthetic field (references → co-citation →
  content-and-authorship prior) and the explore leaderboard rankings, kept in Neon. The synthetic
  field is also computed for any uncached paper via the same fallback chain — but **only behind a
  behavior gate** (see "Bot gate" below): never on a server page GET, only via a client-triggered,
  cached endpoint, so a flat crawler GET can't trigger the ~15-40-call compute.

The legitimate reason to store `works` is to **compute the cohort distributions, fit
calibration, and power the explore leaderboards** — not to be the display source of truth for
a single paper. So the paper page should construct itself live; `works` becomes a compute
input refreshed by the monthly cron, never the display truth.

## What changes

`paper/[oaid]` and `GET /api/qal/:oaid` build the record like this:

1. **Display (live):** fetch the work from OpenAlex (`/works/{oaid}`, selected fields),
   mapped to title, authors (apply the §12 rule: all co-authors when < 11, else "First et
   al."), venue, year, DOI, cited_by_count, biblio, primary subfield (id + label) and field,
   is_oa, is_retracted, reference count. **Always current** — the staleness bug class is gone.
   Cached with Next.js `fetch` revalidation (≈1 day) so repeat views don't re-hit OpenAlex.
2. **Field percentile (cheap, O(1) for every subfield):** the paper's full-population mid-rank
   percentile in its (subfield, year) cohort — an O(1) floor lookup on the precomputed
   `cohort_percentiles` CDF, **no API call, for any subfield**. (Originally a live count query for
   non-seed subfields; the V1.0 factory — `pipeline/factory.py` — now builds `cohort_percentiles`
   for all 252 subfields from the bulk snapshot, so the lookup is universal.) Works for any
   OpenAlex paper, not just the ~371k we pulled.
3. **Layer-B QaL + composition (cached, not recomputed live):** read the precomputed QaL
   from `qal_records` (point, 90% interval, NSF buckets, both field/synthetic metrics) and the
   composition from `synthetic_field`. **The calibration math stays in Python only** — we do
   not port `predict_cell` to TS (one source of truth, no drift). QaL refreshes monthly per
   §11, so cached numbers + live display is the intended read-through; mild lag between
   live `cited_by_count` and last-batch QaL is expected and immaterial (QaL moves slowly).
4. **Uncomputed papers (universal layer, on the fly):** if a paper has no `qal_records` row
   (any OpenAlex id we haven't batched), show the live display plus the observed field
   percentile from a `cohort_percentiles` CDF lookup (seed) — a trivial, low-risk TS floor
   lookup — marked calibration-pending. The calibrated posterior stays scope-bound (§5).

The only new TS math is the cohort-CDF floor lookup; the calibration and synthetic field stay
in Python. `qal_records`/`synthetic_field` (the caches) and `getExplore` (leaderboards) are
**unchanged** — the batch maintains them; the explore table keeps the stored snapshot
(refreshed monthly; its bylines self-heal on the next pull). Only the single-paper detail
view goes live for display.

## Bot gate — the synthetic compute (the one metered op)

The universal layer (live display + the O(1) field percentile) is free and served to everyone,
bots included. The **synthetic field** is the only expensive op (~15-40 OpenAlex calls), so it's
gated by *behavior*, not a challenge:

- It is **never** computed on a server page GET. `getPaperRecord` serves cache-only — `qal_records`
  + a `synthetic_cache` table (any oaid, no FK to `works`) + the universal layer.
- It is computed **only** by `POST /api/synthetic/:oaid`, called by a client island
  (`SyntheticLoader`) after the page mounts in a real browser. Flat crawler GETs (no JS) never fire
  it; they get the universal layer. The result caches in `synthetic_cache`, so each paper computes
  at most once and the next render serves the official synthetic field for free.
- Bounds: the cache (compute-once) + a per-instance concurrency guard + the Vercel edge rate-limit
  (extend the `/paper` rule to `/api/synthetic` for the global cap).
- This **replaced an earlier hard index-gate** that returned "not indexed" for any uncached paper —
  a blunt guard added during a crawler-budget incident. The budget vector was the *premium* OpenAlex
  key (now retired: the web runs all-polite, so the synthetic's calls are free; only rate, not
  dollars, is at stake).

## Consequences

- The author / citation-count staleness bug **cannot recur** on the paper page (live fetch).
- Any OpenAlex Work ID can be scored on the paper page (the POC promise), not only stored ones.
- No author `--all` backfill needed — that hack is superseded.
- Cost: ~1 *free* single-record OpenAlex call per (uncached) paper view for display; the field
  percentile is now a pure DB lookup (no extra calls). The synthetic's ~15-40 calls run only behind
  the behavior gate, free on the polite pool, and cache per paper. The U1 loading skeleton covers
  the added latency. At scale the V1.0 bulk snapshot (factory) removes the live cohort dependency.
- Vercel still does no heavy compute — only the §11-sanctioned cheap path.

## Implementation

- `web/lib/openalex.ts` — live work fetch + mapping (+ §12 byline), Next revalidate cache.
- `web/lib/queries.ts` — `getPaperRecord(oaid)`: fetch live display, then serve **cache-only** —
  the `synthetic_cache` synthetic field if present, else the cached `qal_records` posterior, else
  the universal layer (cohort-CDF floor lookup + calibration-pending/maturity). No synthetic compute
  on this path. Also `computeSyntheticDisplay(oaid)` (the expensive synthetic→display payload) and
  the `synthetic_cache` read/write helpers (lazy `CREATE TABLE IF NOT EXISTS`). Paper page + `/api/qal` call `getPaperRecord`.
- `web/app/api/synthetic/[oaid]/route.ts` — `POST`-only endpoint: runs `computeSyntheticDisplay`,
  writes `synthetic_cache`, returns `{ok}`. The only place the synthetic is computed live.
- `web/components/SyntheticLoader.tsx` — client island on the paper page: after mount, POSTs the
  endpoint when the served record isn't yet synthetic, then `router.refresh()` to swap in the
  official synthetic headline. The behavior gate.
- `db/migrations/006_synthetic_cache.sql` — the serving cache table (also created lazily by the app).
- `OPENALEX_MAILTO` available to the serverless runtime (env, with a code default).
