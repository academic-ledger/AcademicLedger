"""Backfill works.raw->authors under the author-display rule (QaL_spec.md §12):
list all co-authors when fewer than 11, else "First author et al."

Earlier pulls stored only "First author et al." for everything. This re-fetches
authorships (batched) and rewrites the display string. The monthly refresh pull applies
the same rule corpus-wide; this updates already-stored works without a full re-pull.

Usage:
  DATABASE_URL=... python pipeline/backfill_authors.py            # visible set (authors + neighborhoods)
  DATABASE_URL=... python pipeline/backfill_authors.py --all      # every stored work
"""
import os
import json
import time
import argparse

import requests

API = "https://api.openalex.org/works"
MAILTO = os.environ.get("OPENALEX_MAILTO", "")
UA = {"User-Agent": f"al-pipeline/1.0 ({MAILTO})"}


def author_string(authorships):
    names = [n for n in ((a.get("author") or {}).get("display_name")
                         for a in (authorships or [])) if n]
    if not names:
        return None
    return ", ".join(names) if len(names) < 11 else names[0] + " et al."


def fetch_authors(oaids):
    """{oaid: author_string} for a list of oaids, batched 100/call."""
    out = {}
    for i in range(0, len(oaids), 100):
        chunk = oaids[i:i + 100]
        params = {"filter": f"ids.openalex:{'|'.join(chunk)}",
                  "select": "id,authorships", "per-page": 100}
        if MAILTO:
            params["mailto"] = MAILTO
        r = requests.get(API, params=params, timeout=60, headers=UA)
        r.raise_for_status()
        for w in r.json().get("results", []):
            out[w["id"].split("/")[-1]] = author_string(w.get("authorships"))
        time.sleep(0.1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="backfill every stored work")
    args = ap.parse_args()
    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL not set")
    import psycopg
    conn = psycopg.connect(db)
    with conn.cursor() as cur:
        if args.all:
            cur.execute("SELECT oaid FROM works")
        else:
            cur.execute("""SELECT work_oaid FROM author_works
                           UNION SELECT oaid FROM neighborhoods""")
        oaids = [r[0] for r in cur.fetchall()]
    print(f"backfilling authors for {len(oaids)} works", flush=True)

    updated = 0
    for i in range(0, len(oaids), 100):
        chunk = oaids[i:i + 100]
        mapping = fetch_authors(chunk)
        params = [(s, oid) for oid, s in mapping.items() if s]
        with conn.cursor() as cur:
            cur.executemany(
                "UPDATE works SET raw = jsonb_set(coalesce(raw,'{}'::jsonb), '{authors}', "
                "to_jsonb(%s::text)) WHERE oaid=%s", params)
        conn.commit()
        updated += len(params)
        if (i // 100) % 10 == 0:
            print(f"  {updated} updated...", flush=True)
    print(f"done: {updated} works updated")
    conn.close()


if __name__ == "__main__":
    main()
