# Design note — paper page construction: on-the-fly / read-through

**Status:** design for an architectural change, then implementation.
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
  field is also computed **on the fly** for any uncached paper via the same fallback chain, and a
  pre-synthetic cached row is upgraded to it on read.

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
2. **Field percentile (cheap):** the paper's full-population mid-rank percentile in its
   (subfield, year) cohort. For the **seed** subfields (1800/1802/1803, in `cohort_percentiles`)
   it's an O(1) CDF lookup — no API call. For **other** subfields, two live count queries
   (`>cites`, `==cites`) + the cohort total and p₀ — the same exact full-population rule as the
   batch (`pct_in_cohort`). Works for any OpenAlex paper, not just the ~371k we pulled.
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

## Consequences

- The author / citation-count staleness bug **cannot recur** on the paper page (live fetch).
- Any OpenAlex Work ID can be scored on the paper page (the POC promise), not only stored ones.
- No author `--all` backfill needed — that hack is superseded.
- Cost: ~1 OpenAlex call per (uncached) paper view, +2 for non-seed subfields; bounded by
  Next fetch-revalidation and the polite-pool mailto. The U1 loading skeleton already covers
  the added latency. At scale the V1.0 bulk snapshot removes the live dependency.
- Vercel still does no heavy compute — only the §11-sanctioned cheap path.

## Implementation

- `web/lib/openalex.ts` — live work fetch + mapping (+ §12 byline), Next revalidate cache.
- `web/lib/queries.ts` — `getPaperRecord(oaid)`: fetch live display, merge the cached
  `qal_records` QaL + `synthetic_field` composition; for uncomputed papers, a small
  cohort-CDF floor lookup → universal layer + calibration-pending. Paper page + `/api/qal`
  call it. `getQalRecord` (DB-only display) is retired in favor of this.
- `OPENALEX_MAILTO` available to the serverless runtime (env, with a code default).
