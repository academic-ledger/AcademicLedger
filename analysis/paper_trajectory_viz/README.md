# Paper trajectory viz — "A growth chart for a paper"

The interactive research note at **`/research-note.html`** (linked from the site nav): reading a
paper's citation trajectory like a pediatric growth chart, and how QaL forecasts its eventual rank.
Built entirely on real data.

## What it shows
1. **The heavy tail** — cohort citation percentile bands on a log axis (median never leaves zero;
   55.6% uncited; one star at 1,759). Why a raw count is uninterpretable.
2. **The growth chart** — the same papers in *within-field percentile* space, crossing the bands.
   The archetypes (star / sleeper / solid / flash / typical) are real papers picked by trajectory
   shape, not by name.
3. **The forecast fan** — QaL's 90% interval for a paper's *eventual* percentile, narrowing as it
   matures (the sleeper runs [28, 76] at year 2 → [98, 99] at year 10).

## Data
Cohort: OpenAlex subfield **1803** (Management Science & Operations Research), publication years
**2011–2014**, pooled by paper age, a **deterministic 25% hash sample** (`mod(abs(hashtext(oaid)),100)<25`)
of the ~99k full set — bands are stable at this size (N ≈ 24,791). Cumulative citations from OpenAlex
`counts_by_year`; percentile is a full-population mid-rank within the cohort at each age; the forecast
interval is the empirical 5/50/95th percentile of eventual (age-10) standing among papers with the
same observed citations at that age — the back-tested core of QaL's Layer B (production adds the
conformal correction for guaranteed coverage).

## Rebuild
```bash
cd analysis/paper_trajectory_viz
# pull a fresh cohort from Neon and rebuild the page (needs DATABASE_URL via pipeline/_env):
PYTHONPATH=../../pipeline ../../.venv/bin/python build.py
# or rebuild the page from the cached JSON, no DB:
../../.venv/bin/python build.py --no-pull
```

## Files
- `build.py` — pull → compute → inject into template → `web/public/research-note.html`.
- `template.html` — the standalone page, with a `__DATA__` placeholder.
- `trajectory_viz_data.json` — the cached computed dataset (rebuild the page offline with `--no-pull`).

A private, shareable interactive copy also lives as a Claude artifact (see the team's notes).
