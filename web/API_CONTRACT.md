# Read API contract (Vercel route handlers in the Next.js app)

The web app is read-only against the datastore. All write paths are the batch pipeline.

## GET /api/qal/:oaid
Return the served QaL record for one work (joins works + qal_records).
```
{
  "oaid":"W4385447813","doi":"10.xxxx/...","title":"...","year":2023,
  "reference_class":{"field":"subfields/1803","field_label":"Management Science & OR","vintage_year":2023,"n":45452},
  "obs_percentile":98.7,
  "calibrated":true,
  "qal":{"point":96,"ci90":[90,99],"class_prob":{"ge50":1.0,"ge75":0.99,"ge90":0.93,"ge95":0.62,"ge99":0.21}},
  "evidence":{"cited_by_count":166,"is_oa":true,"is_retracted":false},
  "method_version":"qal-0.1","data_snapshot":"openalex-2026-05"
}
```
If `calibrated` is false, omit `qal` and surface `obs_percentile` with a `calibration-pending` status (mirror the mock behavior).

## GET /api/author/:oaid
Author header + their works list (each item is the same shape the explore/author tables consume).

## GET /api/explore?field=&since=&q=&calibrated_only=&sort=&limit=
Filtered, ranked record list. Sorts: qal | cites | year. `field` = subfield id.

Notes
- The official reference class is the co-citation neighborhood; the `field` percentile is the exploration view (QaL_spec.md §3).
- Never compute a single author-level score (author page shows a distribution; QaL_spec.md §5 / mock rationale).
