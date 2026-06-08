"""Co-citation neighborhood (RCR; Hutchins et al. 2016) — the OFFICIAL reference class.

A paper P's neighborhood is the set of works it travels with in reference lists: take the
works that cite P, pool THEIR reference lists, and the most-co-cited works (excluding P)
are P's co-citation neighborhood. P's official standing is its percentile within that
neighborhood, by age-normalized citation rate (cites / years-since-publication), so the
benchmark is robust to OpenAlex's single-primary-field misclassification.

This is a graph computation (dozens to hundreds of OpenAlex calls per paper), so it is run
in BATCH and cached in `neighborhoods` (QaL_spec.md §11; Vercel never does this). Papers
with too-thin co-citation are skipped and fall back to the field reference class.

Usage:
  DATABASE_URL=... python pipeline/neighborhood.py --targets seed-and-leaders --per-community 100
  DATABASE_URL=... python pipeline/neighborhood.py --oaids W123,W456
Env: OPENALEX_MAILTO, AS_OF_YEAR (default 2026), OPENALEX_SNAPSHOT.
"""
import os
import json
import time
import argparse
from collections import Counter

import requests

API = "https://api.openalex.org/works"
MAILTO = os.environ.get("OPENALEX_MAILTO", "")
AS_OF = int(os.environ.get("AS_OF_YEAR", "2026"))
SNAPSHOT = os.environ.get("OPENALEX_SNAPSHOT", "openalex-dev")
UA = {"User-Agent": f"al-pipeline/1.0 ({MAILTO})"}

# Cost / quality knobs.
MAX_CITERS = 1000      # cap citing works scanned (top co-cited members stabilize quickly)
NEIGH_SIZE = 200       # neighborhood = top-K most co-cited works
MIN_CITERS = 8         # below this, co-citation is too thin -> fall back to field class
MIN_NEIGH = 30         # need at least this many neighbors for a meaningful percentile


def _get(params):
    if MAILTO:
        params["mailto"] = MAILTO
    r = requests.get(API, params=params, timeout=60, headers=UA)
    r.raise_for_status()
    return r.json()


def citers_referenced_works(oaid):
    """Yield the referenced_works list of each work citing `oaid` (capped at MAX_CITERS)."""
    seen = 0
    cursor = "*"
    while cursor and seen < MAX_CITERS:
        d = _get({"filter": f"cites:{oaid}", "select": "id,referenced_works",
                  "per-page": 200, "cursor": cursor})
        for w in d["results"]:
            yield w.get("referenced_works") or []
            seen += 1
        cursor = d["meta"].get("next_cursor")
        time.sleep(0.1)
    return


def member_rates(oaids):
    """Fetch cited_by_count + publication_year for member works; return {oaid: rate}."""
    rates = {}
    ids = list(oaids)
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        pipe = "|".join(chunk)
        d = _get({"filter": f"ids.openalex:{pipe}", "select": "id,cited_by_count,publication_year",
                  "per-page": 100})
        for w in d["results"]:
            oid = w["id"].split("/")[-1]
            yr = w.get("publication_year") or AS_OF
            age = max(1, AS_OF - yr + 1)
            rates[oid] = (w.get("cited_by_count", 0) or 0) / age
        time.sleep(0.1)
    return rates


def build_neighborhood(oaid):
    """Return a neighborhood record dict, or None if co-citation is too thin."""
    counts = Counter()
    n_citers = 0
    full = f"https://openalex.org/{oaid}"
    for refs in citers_referenced_works(oaid):
        n_citers += 1
        for r in refs:
            if r != full:                      # exclude P itself
                counts[r.split("/")[-1]] += 1
    if n_citers < MIN_CITERS:
        return None
    # neighborhood = the top-K most-co-cited works
    top = [oid for oid, _ in counts.most_common(NEIGH_SIZE)]
    if len(top) < MIN_NEIGH:
        return None
    rates = member_rates(top + [oaid])
    p_rate = rates.get(oaid)
    if p_rate is None:
        return None
    member_rate_vals = [rates[o] for o in top if o in rates]
    if len(member_rate_vals) < MIN_NEIGH:
        return None
    pool = sorted(member_rate_vals + [p_rate])
    # percentile = share of the neighborhood (incl. P) at or below P's rate
    import bisect
    pct = 100.0 * bisect.bisect_right(pool, p_rate) / len(pool)
    members = [{"oaid": oid, "cocite": counts[oid], "rate": round(rates.get(oid, 0.0), 3)}
               for oid in top[:25] if oid in rates]
    return {
        "oaid": oaid,
        "n_neighbors": len(member_rate_vals),
        "n_citers": n_citers,
        "obs_percentile": round(pct, 2),
        "members": members,
    }


def target_oaids(conn, mode, per_community):
    with conn.cursor() as cur:
        if mode == "seed-and-leaders":
            cur.execute("SELECT DISTINCT work_oaid FROM author_works")
            oaids = {r[0] for r in cur.fetchall()}
            for sid in ("1803", "1802", "1800"):
                cur.execute(
                    """SELECT q.oaid FROM qal_records q JOIN works w ON w.oaid=q.oaid
                       WHERE w.primary_subfield=%s AND q.obs_percentile IS NOT NULL
                       ORDER BY q.obs_percentile DESC, w.cited_by_count DESC LIMIT %s""",
                    (sid, per_community),
                )
                oaids.update(r[0] for r in cur.fetchall())
            return sorted(oaids)
    return []


def upsert(conn, rec):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO neighborhoods (oaid,n_neighbors,n_citers,obs_percentile,members,snapshot)
               VALUES (%s,%s,%s,%s,%s,%s)
               ON CONFLICT (oaid) DO UPDATE SET
                 n_neighbors=EXCLUDED.n_neighbors, n_citers=EXCLUDED.n_citers,
                 obs_percentile=EXCLUDED.obs_percentile, members=EXCLUDED.members,
                 snapshot=EXCLUDED.snapshot, computed_at=now()""",
            (rec["oaid"], rec["n_neighbors"], rec["n_citers"], rec["obs_percentile"],
             json.dumps(rec["members"]), SNAPSHOT),
        )
    conn.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default="", help="'seed-and-leaders'")
    ap.add_argument("--per-community", type=int, default=100)
    ap.add_argument("--oaids", default="", help="comma-separated oaids to compute directly")
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL not set")
    import psycopg
    conn = psycopg.connect(db)

    if args.oaids:
        oaids = [s.strip() for s in args.oaids.split(",") if s.strip()]
    else:
        oaids = target_oaids(conn, args.targets, args.per_community)
    print(f"computing neighborhoods for {len(oaids)} papers", flush=True)

    built = skipped = 0
    for i, oaid in enumerate(oaids, 1):
        try:
            rec = build_neighborhood(oaid)
        except requests.HTTPError as e:
            print(f"  [{i}] {oaid}: HTTP error {e}", flush=True)
            continue
        if rec is None:
            skipped += 1
            continue
        upsert(conn, rec)
        built += 1
        if i % 25 == 0:
            print(f"  [{i}/{len(oaids)}] built={built} skipped(thin)={skipped}", flush=True)
    print(f"done: {built} neighborhoods cached, {skipped} too thin (field fallback)")
    conn.close()


if __name__ == "__main__":
    main()
