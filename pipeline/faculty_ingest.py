"""Ingest the OID faculty's papers into the corpus so they appear in explore/leaderboards.

For each verified faculty author (pipeline/oid_faculty_ids.yml): pull their works into `works`
(reusing pull_cohort's row mapper, so display fields + per-author authorships are captured), and
populate `authors` + `author_works`. Then synthetic_field (--targets faculty) and compute_qal give
them the official QaL. Many faculty papers (e.g. Cachon's 2003 chapter) sit outside the sampled
cohorts, so without this they only resolve on their own live paper page, never in explore.

Usage:  DATABASE_URL=... OPENALEX_MAILTO=... python pipeline/faculty_ingest.py [--top N]
"""
import os
import time
import json
import argparse

import requests
import yaml

import pull_cohort as pc  # reuse SELECT, _row, upsert

WORKS = "https://api.openalex.org/works"
AUTHORS = "https://api.openalex.org/authors"
MAILTO = os.environ.get("OPENALEX_MAILTO", "")
API_KEY = os.environ.get("OPENALEX_API_KEY", "")
UA = {"User-Agent": f"al-pipeline/1.0 ({MAILTO})"}


def _get(url, params, tries=6):
    if MAILTO:
        params["mailto"] = MAILTO
    if API_KEY:
        params["api_key"] = API_KEY
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, timeout=60, headers=UA)
        except requests.exceptions.RequestException:
            time.sleep(min(30, 2 ** attempt))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(min(30, 2 ** attempt))
            continue
        r.raise_for_status()
        return r.json()
    raise requests.exceptions.RequestException("OpenAlex retries exhausted")


def faculty_ids():
    """surname -> OpenAlex author id (verified overrides only)."""
    m = yaml.safe_load(open("pipeline/oid_faculty_ids.yml")) or {}
    return {str(k): str(v) for k, v in m.items() if v}


def author_entity(aid):
    d = _get(f"{AUTHORS}/{aid}",
             {"select": "id,display_name,orcid,last_known_institutions,works_count,cited_by_count"})
    inst = (d.get("last_known_institutions") or [{}])
    inst = inst[0].get("display_name") if inst else None
    return {"oaid": d["id"].split("/")[-1], "name": d.get("display_name"), "orcid": d.get("orcid"),
            "aff": inst, "works_count": d.get("works_count"), "cites": d.get("cited_by_count")}


def author_works(aid, top):
    """_row dicts for an author's most-cited works, capped at `top`."""
    out, per = [], 200
    pages = (top + per - 1) // per
    for page in range(1, pages + 1):
        d = _get(WORKS, {"filter": f"authorships.author.id:{aid}", "select": pc.SELECT,
                         "per-page": per, "page": page, "sort": "cited_by_count:desc"})
        res = d.get("results", [])
        if not res:
            break
        for w in res:
            out.append(pc._row(w))
            if len(out) >= top:
                return out
        time.sleep(0.1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=100, help="most-cited works per faculty to ingest")
    args = ap.parse_args()
    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL not set")
    import psycopg
    conn = psycopg.connect(db, keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5)

    fac = faculty_ids()
    print(f"ingesting up to {args.top} works each for {len(fac)} faculty", flush=True)
    total = 0
    for surname, aid in fac.items():
        try:
            ent = author_entity(aid)
            works = author_works(aid, args.top)
        except requests.exceptions.RequestException as e:
            print(f"  {surname}: skipped ({str(e)[:50]})", flush=True)
            continue
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO authors (oaid,orcid,display_name,affiliation,works_count,cited_by_count,seed)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (oaid) DO UPDATE SET display_name=EXCLUDED.display_name,
                     affiliation=EXCLUDED.affiliation, works_count=EXCLUDED.works_count,
                     cited_by_count=EXCLUDED.cited_by_count""",
                (ent["oaid"], ent["orcid"], ent["name"], ent["aff"], ent["works_count"],
                 ent["cites"], ["1803", "1802", "1800"]))
        conn.commit()
        if works:
            pc.upsert(conn, works)  # -> works table (display + authorships)
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO author_works (author_oaid,work_oaid) VALUES (%s,%s) "
                    "ON CONFLICT DO NOTHING",
                    [(aid, w["oaid"]) for w in works])
            conn.commit()
        total += len(works)
        print(f"  {surname:14s} {ent['name']}: {len(works)} works", flush=True)
    conn.close()
    print(f"done: ingested {total} faculty works")


if __name__ == "__main__":
    main()
