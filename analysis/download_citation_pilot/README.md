# Download → citation pilot (Paper B, Result 2)

Do early PDF downloads predict eventual citations? A pilot for the economics (RePEc/LogEc) study,
run on preprint servers because they expose **open per-article download data**. Full writeup and
caveats: [`docs/download_citation_pilot_result.md`](../../docs/download_citation_pilot_result.md).

## Headline
Early downloads predict eventual citations at **Spearman ρ ≈ 0.35 (medRxiv 2019, medicine)** to
**0.47 (bioRxiv 2017, biology)**, **plateauing by ~3–6 months** — in the Brody (physics, ~0.4) /
Perneger (medicine, ~0.5) band, now shown in-domain with modern data. Real but bounded: the case for
"admit broadly, decide late." See `fig_download_citation.png`.

## Why a preprint pilot (not economics yet)
The economics version is blocked on data access: LogEc's per-item download pages are under `/scripts/`,
which `robots.txt` disallows, so the counts must be **requested** from the RePEc maintainers (pending),
not scraped. Preprint servers publish open per-article downloads, so the pipeline can be validated now.

## Rebuild
```bash
# 1. get the open Rxivist dump (~493 MiB, Postgres custom-format) from Zenodo:
curl -sL -o rxivist.backup "https://zenodo.org/records/7688682/files/rxivist.backup?download=1"
../../.venv/bin/pip install pgdumplib
# 2. extract per-article early downloads + join OpenAlex citations -> rxiv_cohort_merged.json:
../../.venv/bin/python extract_downloads.py rxivist.backup
# 3. correlations + figure (also runs standalone on the cached merged JSON):
../../.venv/bin/python analyze.py
```

## Files
- `analyze.py` — merged cohort → Spearman-by-window, AUC, `fig_download_citation.png`, `results.json`.
- `extract_downloads.py` — Rxivist dump → per-article early downloads → OpenAlex citation join.
- `rxiv_cohort_merged.json` — cached cohort (downloads @1/3/6/12mo + eventual citations); rerun
  `analyze.py` on it with no network or dump.
- `results.json`, `fig_download_citation.png` — outputs.

## Data
Rxivist dump: Abdill & Blekhman, Zenodo `10.5281/zenodo.7688682` (crawl frozen 2023-02). The 493 MiB
`rxivist.backup` is **not committed** — download it from Zenodo. Citations: OpenAlex (CC0).
