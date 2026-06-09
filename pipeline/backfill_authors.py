"""Backfill works.raw with per-author identity for clickable bylines (QaL_spec.md §9/§12).

Re-fetches authorships (batched, 100/call) and merges into works.raw BOTH the display string
(`authors`, §12 rule) AND the per-author identities (`authorships`: [{name, oaid, orcid}]) that
let every author name link to its author page. compute_qal then folds these into qal_records.display,
so the explore/leaderboard tables render linked authors at zero request-time cost. Resumable: only
touches works that don't already carry `raw.authorships`.

Usage:
  DATABASE_URL=... python pipeline/backfill_authors.py            # the seeded-author set
  DATABASE_URL=... python pipeline/backfill_authors.py --all      # every stored work (resumable)
"""
import os
import json
import time
import argparse

import requests

API = "https://api.openalex.org/works"
MAILTO = os.environ.get("OPENALEX_MAILTO", "")
API_KEY = os.environ.get("OPENALEX_API_KEY", "")  # premium key: lifts the daily list budget
UA = {"User-Agent": f"al-pipeline/1.0 ({MAILTO})"}


def author_string(authorships):
    names = [n for n in ((a.get("author") or {}).get("display_name")
                         for a in (authorships or [])) if n]
    if not names:
        return None
    return ", ".join(names) if len(names) < 11 else names[0] + " et al."


def authorships_of(authorships):
    """Per-author identity for clickable bylines (QaL_spec §9): [{name, oaid, orcid}]."""
    return [
        {"name": (a.get("author") or {}).get("display_name"),
         "oaid": ((a.get("author") or {}).get("id") or "").split("/")[-1] or None,
         "orcid": (a.get("author") or {}).get("orcid")}
        for a in (authorships or []) if (a.get("author") or {}).get("display_name")
    ]


def fetch_authorships(oaids):
    """{oaid: (author_string, authorships_list)} for a list of oaids, batched 100/call."""
    out = {}
    for i in range(0, len(oaids), 100):
        chunk = oaids[i:i + 100]
        params = {"filter": f"ids.openalex:{'|'.join(chunk)}",
                  "select": "id,authorships", "per-page": 100}
        if MAILTO:
            params["mailto"] = MAILTO
        if API_KEY:
            params["api_key"] = API_KEY
        r = requests.get(API, params=params, timeout=60, headers=UA)
        r.raise_for_status()
        for w in r.json().get("results", []):
            ships = w.get("authorships")
            out[w["id"].split("/")[-1]] = (author_string(ships), authorships_of(ships))
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
            # resumable: only works that don't already carry per-author identity
            cur.execute("SELECT oaid FROM works WHERE NOT (raw ? 'authorships')")
        else:
            cur.execute("SELECT work_oaid FROM author_works")
        oaids = [r[0] for r in cur.fetchall()]
    print(f"backfilling authorships for {len(oaids)} works", flush=True)

    updated = 0
    for i in range(0, len(oaids), 100):
        chunk = oaids[i:i + 100]
        mapping = fetch_authorships(chunk)
        # merge BOTH the display string and the per-author identities into raw, preserving the
        # other raw keys (venue, subfield_label). `||` overwrites only the two keys we set.
        params = [(json.dumps(ships), s, oid)
                  for oid, (s, ships) in mapping.items() if ships]
        with conn.cursor() as cur:
            cur.executemany(
                "UPDATE works SET raw = coalesce(raw,'{}'::jsonb) "
                "|| jsonb_build_object('authorships', %s::jsonb, 'authors', %s::text) "
                "WHERE oaid=%s", params)
        conn.commit()
        updated += len(params)
        if (i // 100) % 10 == 0:
            print(f"  {updated} updated...", flush=True)
    print(f"done: {updated} works updated")
    conn.close()


if __name__ == "__main__":
    main()
