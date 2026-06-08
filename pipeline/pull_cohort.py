"""Pull OpenAlex cohorts into the `works` table (or local parquet if no DB).

Generalizes the prototype pulls used to build the mocks. One paginated pass per
(subfield, year), capturing cited_by_count and counts_by_year for the age model.

Usage:  python pipeline/pull_cohort.py --config pipeline/cohorts.yml
"""
import os, sys, time, json, argparse, yaml, requests

API = "https://api.openalex.org/works"
MAILTO = os.environ.get("OPENALEX_MAILTO", "")

def fetch_cohort(subfield, year):
    cursor = "*"
    flt = f"primary_topic.subfield.id:subfields/{subfield},publication_year:{year}"
    while cursor:
        params = {"filter": flt, "per-page": 200, "cursor": cursor,
                  "select": "id,doi,title,publication_year,primary_topic,primary_location,authorships,cited_by_count,counts_by_year,open_access,is_retracted"}
        if MAILTO: params["mailto"] = MAILTO
        r = requests.get(API, params=params, timeout=60, headers={"User-Agent": f"al-pipeline/1.0 ({MAILTO})"})
        r.raise_for_status()
        d = r.json()
        for w in d["results"]:
            pt = w.get("primary_topic") or {}
            sub = (pt.get("subfield") or {})
            # lean display fields stored in raw (authors as "First Author et al.", venue)
            auths = w.get("authorships") or []
            first = ((auths[0].get("author") or {}).get("display_name")) if auths else None
            authors_str = (first + (" et al." if len(auths) > 1 else "")) if first else None
            venue = (((w.get("primary_location") or {}).get("source") or {}).get("display_name"))
            yield {
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
        cursor = d["meta"].get("next_cursor")
        time.sleep(0.1)   # be a good OpenAlex citizen

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="pipeline/cohorts.yml")
    ap.add_argument("--subfields", default="", help="comma-separated subfield ids to limit the pull")
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
            rows = list(fetch_cohort(sid, yr))
            print(f"  {sid} {yr}: {len(rows)} works")
            if conn:
                upsert(conn, rows)
            else:
                os.makedirs("data", exist_ok=True)
                with open(f"data/{sid}_{yr}.jsonl", "w") as f:
                    for row in rows: f.write(json.dumps(row) + "\n")
    if conn: conn.close()

def upsert(conn, rows):
    with conn.cursor() as cur:
        for row in rows:
            cur.execute("""
              INSERT INTO works (oaid,doi,title,publication_year,primary_subfield,primary_field,
                                 cited_by_count,counts_by_year,is_oa,is_retracted,raw)
              VALUES (%(oaid)s,%(doi)s,%(title)s,%(publication_year)s,%(primary_subfield)s,%(primary_field)s,
                      %(cited_by_count)s,%(counts_by_year)s,%(is_oa)s,%(is_retracted)s,%(raw)s)
              ON CONFLICT (oaid) DO UPDATE SET
                cited_by_count=EXCLUDED.cited_by_count, counts_by_year=EXCLUDED.counts_by_year,
                is_retracted=EXCLUDED.is_retracted, primary_subfield=EXCLUDED.primary_subfield,
                primary_field=EXCLUDED.primary_field,
                raw=COALESCE(works.raw, EXCLUDED.raw), fetched_at=now();
            """, {**row, "counts_by_year": json.dumps(row["counts_by_year"]),
                  "raw": json.dumps(row["raw"])})
    conn.commit()

if __name__ == "__main__":
    main()
