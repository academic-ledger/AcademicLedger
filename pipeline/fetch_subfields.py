"""Populate the `subfields` table from the OpenAlex /subfields taxonomy (id -> display name).

The synthetic-field composition (U3) shows a paper's reference-class blend by subfield; this
maps the ~250 subfield ids to human names. One small paginated pull; safe to re-run.

Usage:  DATABASE_URL=... OPENALEX_MAILTO=... python pipeline/fetch_subfields.py
"""
import os
import time

import requests

API = "https://api.openalex.org/subfields"
MAILTO = os.environ.get("OPENALEX_MAILTO", "")


def fetch_all():
    out, page = {}, 1
    while True:
        params = {"per-page": 200, "page": page, "select": "id,display_name"}
        if MAILTO:
            params["mailto"] = MAILTO
        r = requests.get(API, params=params, headers={"User-Agent": f"al-pipeline/1.0 ({MAILTO})"}, timeout=60)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(min(30, 2 ** page))
            continue
        r.raise_for_status()
        res = r.json().get("results", [])
        if not res:
            break
        for x in res:
            out[x["id"].split("/")[-1]] = x["display_name"]
        page += 1
        time.sleep(0.2)
    return out


def main():
    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL not set")
    import psycopg
    names = fetch_all()
    with psycopg.connect(db) as c, c.cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS subfields (id TEXT PRIMARY KEY, name TEXT)")
        cur.executemany(
            "INSERT INTO subfields (id,name) VALUES (%s,%s) ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name",
            list(names.items()))
    print(f"upserted {len(names)} subfield names")


if __name__ == "__main__":
    main()
