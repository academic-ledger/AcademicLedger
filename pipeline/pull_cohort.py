"""Pull OpenAlex cohorts into the `works` table (or local parquet if no DB).

Generalizes the prototype pulls used to build the mocks. One paginated pass per
(subfield, year), capturing cited_by_count and counts_by_year for the age model.

Usage:  python pipeline/pull_cohort.py --config pipeline/cohorts.yml
"""
import os, sys, time, json, argparse, yaml, requests

API = "https://api.openalex.org/works"
MAILTO = os.environ.get("OPENALEX_MAILTO", "")

SELECT = ("id,doi,title,publication_year,primary_topic,primary_location,authorships,"
          "cited_by_count,counts_by_year,open_access,is_retracted")


def _row(w):
    pt = w.get("primary_topic") or {}
    sub = (pt.get("subfield") or {})
    # lean display fields stored in raw (authors as "First Author et al.", venue)
    auths = w.get("authorships") or []
    first = ((auths[0].get("author") or {}).get("display_name")) if auths else None
    authors_str = (first + (" et al." if len(auths) > 1 else "")) if first else None
    venue = (((w.get("primary_location") or {}).get("source") or {}).get("display_name"))
    return {
        "oaid": w["id"].split("/")[-1],
        "doi": w.get("doi"),
        "title": w.get("title"),
        "publication_year": w.get("publication_year"),
        "primary_subfield": str((sub.get("id") or "").split("/")[-1]) or None,
        "primary_field": ((pt.get("field") or {}).get("display_name")),
        "cited_by_count": w.get("cited_by_count", 0),
        "counts_by_year": {str(c["year"]): c["cited_by_count"] for c in (w.get("counts_by_year") or [])},
        "is_oa": ((w.get("open_access") or {}).get("is_oa")),
        "is_retracted": bool(w.get("is_retracted")),
        "raw": {"authors": authors_str, "venue": venue,
                "subfield_label": sub.get("display_name")},
    }


def fetch_cohort(subfield, year, sample=0, seed=42):
    """Yield works in a (subfield, year) cohort.

    sample=0  -> full cohort via cursor pagination (every work).
    sample=N  -> a uniform random sample of up to N works via OpenAlex `sample`
                 (basic page pagination; capped at 10,000 by the API). Statistically
                 sufficient to estimate the citation CDF and the calibration mapping,
                 at a tiny fraction of the storage/time for million-work subfields.
    """
    flt = f"primary_topic.subfield.id:subfields/{subfield},publication_year:{year}"
    if sample and sample > 0:
        n = min(int(sample), 10000)
        per = 200
        for page in range(1, (n // per) + 2):
            params = {"filter": flt, "select": SELECT, "sample": n, "seed": seed,
                      "per-page": per, "page": page}
            if MAILTO: params["mailto"] = MAILTO
            r = requests.get(API, params=params, timeout=60,
                             headers={"User-Agent": f"al-pipeline/1.0 ({MAILTO})"})
            r.raise_for_status()
            results = r.json().get("results", [])
            if not results:
                break
            for w in results:
                yield _row(w)
            time.sleep(0.1)
        return
    cursor = "*"
    while cursor:
        params = {"filter": flt, "per-page": 200, "cursor": cursor, "select": SELECT}
        if MAILTO: params["mailto"] = MAILTO
        r = requests.get(API, params=params, timeout=60, headers={"User-Agent": f"al-pipeline/1.0 ({MAILTO})"})
        r.raise_for_status()
        d = r.json()
        for w in d["results"]:
            yield _row(w)
        cursor = d["meta"].get("next_cursor")
        time.sleep(0.1)   # be a good OpenAlex citizen

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="pipeline/cohorts.yml")
    ap.add_argument("--subfields", default="", help="comma-separated subfield ids to limit the pull")
    ap.add_argument("--sample", type=int, default=0,
                    help="uniform random sample size per cohort (0 = full cohort)")
    ap.add_argument("--seed", type=int, default=42, help="sample seed (reproducible)")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))
    subs = [s.strip() for s in args.subfields.split(",") if s.strip()] or list(cfg["seed_subfields"])
    years = sorted(set(cfg["score_years"] + cfg["calibration_years"]))
    db = os.environ.get("DATABASE_URL")
    conn = None
    if db:
        import psycopg
        conn = psycopg.connect(db)
    for sid in subs:
        for yr in years:
            rows = list(fetch_cohort(sid, yr, sample=args.sample, seed=args.seed))
            print(f"  {sid} {yr}: {len(rows)} works", flush=True)
            if conn:
                upsert(conn, rows)
            else:
                os.makedirs("data", exist_ok=True)
                with open(f"data/{sid}_{yr}.jsonl", "w") as f:
                    for row in rows: f.write(json.dumps(row) + "\n")
    if conn: conn.close()

UPSERT_SQL = """
  INSERT INTO works (oaid,doi,title,publication_year,primary_subfield,primary_field,
                     cited_by_count,counts_by_year,is_oa,is_retracted,raw)
  VALUES (%(oaid)s,%(doi)s,%(title)s,%(publication_year)s,%(primary_subfield)s,%(primary_field)s,
          %(cited_by_count)s,%(counts_by_year)s,%(is_oa)s,%(is_retracted)s,%(raw)s)
  ON CONFLICT (oaid) DO UPDATE SET
    cited_by_count=EXCLUDED.cited_by_count, counts_by_year=EXCLUDED.counts_by_year,
    is_retracted=EXCLUDED.is_retracted, primary_subfield=EXCLUDED.primary_subfield,
    primary_field=EXCLUDED.primary_field,
    raw=COALESCE(works.raw, EXCLUDED.raw), fetched_at=now();
"""

def upsert(conn, rows):
    # executemany pipelines the batch (psycopg3) — far faster than per-row execute.
    params = [{**r, "counts_by_year": json.dumps(r["counts_by_year"]),
               "raw": json.dumps(r["raw"])} for r in rows]
    with conn.cursor() as cur:
        cur.executemany(UPSERT_SQL, params)
    conn.commit()

if __name__ == "__main__":
    main()
