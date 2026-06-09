"""Synthetic field — the OFFICIAL reference class (QaL_spec.md §5 Precise computation).

The focal paper is ranked against a weight-blended full-population cohort distribution
D = Σ_t w_t · cohort(t, v), NOT against its co-citation neighbors. The topic-mixture
weights w_t migrate from reference-based (cold start) to community-based as citations accrue:

  w_t^ref = Σ_i g_i · s_{i,t}      references i, recency g_i = exp(-max(0,v-y_i)/τ), normalized
  w_t^cc  = co-citation neighborhood's topic mixture
  w_t     = (1-λ) w_t^ref + λ w_t^cc,   λ = c/(c+k),  c = citing papers, k≈20

  r_obs = Σ_t w_t · pct_t(focal)   (mixture CDF; mid-rank ties; uncited atom emerges)
  p0    = Σ_t w_t · p0(t, v)

Granularity is subfield-level here (the spec's permitted fallback; topic-level is a
refinement). Each cohort(subfield, v) is fetched once as an OpenAlex cited_by_count
histogram (group_by) and cached. Graph/cohort work is batch-only (Vercel never does it).

Usage: DATABASE_URL=... python pipeline/synthetic_field.py --targets seed-and-leaders
Env: OPENALEX_MAILTO, AS_OF_YEAR (2026), H_HALFLIFE (global cited half-life, default 6),
     K_LAMBDA (20), OPENALEX_SNAPSHOT.
"""
import os
import json
import math
import time
import argparse
from collections import Counter, defaultdict

import requests

API = "https://api.openalex.org/works"
MAILTO = os.environ.get("OPENALEX_MAILTO", "")
AS_OF = int(os.environ.get("AS_OF_YEAR", "2026"))
SNAPSHOT = os.environ.get("OPENALEX_SNAPSHOT", "openalex-dev")
UA = {"User-Agent": f"al-pipeline/1.0 ({MAILTO})"}

TAU = float(os.environ.get("H_HALFLIFE", "6")) / math.log(2)  # recency decay timescale
K_LAMBDA = float(os.environ.get("K_LAMBDA", "20"))
N_MIN_REFS = 5          # usable references below which the reference stage is skipped
MAX_CITERS = 1000       # cap citing works scanned for the community mixture
NEIGH_SIZE = 200        # co-cited works kept for the community topic mixture

_HIST = {}              # (subfield, year) -> {"total", "hist": {cites: count}, "p0"} cached cohorts


def _get(params):
    if MAILTO:
        params["mailto"] = MAILTO
    r = requests.get(API, params=params, timeout=60, headers=UA)
    r.raise_for_status()
    return r.json()


def _sub(work):
    s = (((work.get("primary_topic") or {}).get("subfield") or {}).get("id") or "")
    return s.split("/")[-1] or None


def focal_meta(oaid):
    d = _get({"filter": f"ids.openalex:{oaid}",
              "select": "id,referenced_works,publication_year,cited_by_count,primary_topic",
              "per-page": 1})
    res = d.get("results") or []
    return res[0] if res else None


def works_sub_year(oaids):
    """{oaid: (subfield, year)} for a list of works, batched 100/call."""
    out = {}
    ids = list(oaids)
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        d = _get({"filter": f"ids.openalex:{'|'.join(chunk)}",
                  "select": "id,publication_year,primary_topic", "per-page": 100})
        for w in d["results"]:
            out[w["id"].split("/")[-1]] = (_sub(w), w.get("publication_year"))
        time.sleep(0.1)
    return out


def cohort_hist(subfield, year):
    """Cached cited_by_count histogram of the (subfield, year) cohort, with total and p0."""
    key = (subfield, year)
    if key in _HIST:
        return _HIST[key]
    # per-page also caps the number of group buckets returned (up to 200) — must request 200,
    # not 1, or only the single largest bucket (cited_by_count=0) comes back.
    d = _get({"filter": f"primary_topic.subfield.id:subfields/{subfield},publication_year:{year}",
              "group_by": "cited_by_count", "per-page": 200})
    total = d["meta"]["count"]
    hist = {int(g["key"]): g["count"] for g in (d.get("group_by") or []) if str(g["key"]).isdigit()}
    _HIST[key] = {"total": total, "hist": hist,
                  "p0": (hist.get(0, 0) / total if total else None)}
    time.sleep(0.1)
    return _HIST[key]


def pct_in_cohort(subfield, year, cites):
    """Focal's MID-RANK percentile (fraction in [0,1]) within (subfield, year), and that
    cohort's p0. Histogram is top-200 by frequency, so the rare high tail may be clipped;
    immaterial for the low/mid mass that dominates the percentile."""
    h = cohort_hist(subfield, year)
    if not h["total"]:
        return None, None
    below = sum(c for k, c in h["hist"].items() if k < cites)
    equal = h["hist"].get(cites, 0)
    return (below + equal / 2.0) / h["total"], h["p0"]


def cocitation_counts(oaid):
    """Counter {co-cited oaid: co-citation count} and the number of citing works scanned."""
    counts = Counter()
    n_citers = 0
    full = f"https://openalex.org/{oaid}"
    cursor = "*"
    while cursor and n_citers < MAX_CITERS:
        d = _get({"filter": f"cites:{oaid}", "select": "id,referenced_works",
                  "per-page": 200, "cursor": cursor})
        for w in d["results"]:
            n_citers += 1
            for r in (w.get("referenced_works") or []):
                if r != full:
                    counts[r.split("/")[-1]] += 1
        cursor = d["meta"].get("next_cursor")
        time.sleep(0.1)
    return counts, n_citers


def _normalize(d):
    tot = sum(d.values())
    return {k: v / tot for k, v in d.items()} if tot else {}


def synthetic_field(oaid):
    """Compute the synthetic-field r_obs for one work. Returns a record dict or None."""
    w = focal_meta(oaid)
    if not w:
        return None
    v = w.get("publication_year") or AS_OF
    cites = w.get("cited_by_count", 0) or 0
    focal_sub = _sub(w)

    # --- reference stage: recency-weighted subfield mixture of the bibliography ---
    refs = [r.split("/")[-1] for r in (w.get("referenced_works") or [])]
    w_ref = defaultdict(float)
    usable = 0
    if refs:
        meta = works_sub_year(refs)
        for sub, y in meta.values():
            if not sub:
                continue
            g = math.exp(-max(0, v - (y or v)) / TAU)
            w_ref[sub] += g
            usable += 1

    # --- community stage: co-citation neighborhood subfield mixture ---
    counts, n_citers = cocitation_counts(oaid)
    w_cc = defaultdict(float)
    if counts:
        top = [o for o, _ in counts.most_common(NEIGH_SIZE)]
        for o, (sub, _y) in works_sub_year(top).items():
            if sub:
                w_cc[sub] += counts[o]

    has_ref = usable >= N_MIN_REFS
    has_cc = len(w_cc) > 0
    if not has_ref and not has_cc:
        # fallback: the focal's own (subfield, vintage) cohort, single-topic special case
        weights = {focal_sub: 1.0} if focal_sub else {}
        lam = None
    else:
        nref, ncc = _normalize(w_ref), _normalize(w_cc)
        if has_ref and has_cc:
            lam = n_citers / (n_citers + K_LAMBDA)
        elif has_ref:
            lam = 0.0
        else:
            lam = 1.0
        subs = set(nref) | set(ncc)
        weights = {s: (1 - lam) * nref.get(s, 0.0) + lam * ncc.get(s, 0.0) for s in subs}

    if not weights:
        return None

    # --- rank against the blended cohort distribution D ---
    r = p0 = wused = 0.0
    for s, ws in weights.items():
        pct, p0s = pct_in_cohort(s, v, cites)
        if pct is None:
            continue
        r += ws * pct
        p0 += ws * (p0s or 0.0)
        wused += ws
    if wused < 0.5:  # most weight had no cohort -> fallback to focal subfield
        pct, p0s = pct_in_cohort(focal_sub, v, cites)
        if pct is None:
            return None
        r, p0, wused = pct, (p0s or 0.0), 1.0

    return {
        "oaid": oaid,
        "obs_percentile": round(100 * r / wused, 2),
        "p0": round(p0 / wused, 4),
        "lam": None if lam is None else round(lam, 3),
        "n_refs": usable,
        "n_citers": n_citers,
        "weights": {s: round(ws, 3) for s, ws in sorted(weights.items(), key=lambda x: -x[1])[:8]},
        # cold-start placement (reference-only), for transparency / the sanity check
        "r_obs_ref_only": _ref_only_pct(_normalize(w_ref), v, cites) if usable else None,
    }


def _ref_only_pct(nref, v, cites):
    if not nref:
        return None
    r = wused = 0.0
    for s, ws in nref.items():
        pct, _ = pct_in_cohort(s, v, cites)
        if pct is not None:
            r += ws * pct
            wused += ws
    return round(100 * r / wused, 2) if wused else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default="")
    ap.add_argument("--per-community", type=int, default=100)
    ap.add_argument("--oaids", default="")
    args = ap.parse_args()
    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL not set")
    import psycopg
    with psycopg.connect(db) as c0, c0.cursor() as cur:
        if args.oaids:
            oaids = [s.strip() for s in args.oaids.split(",") if s.strip()]
        else:
            oaids = _target_oaids(c0, args.targets, args.per_community)
        # resume: skip papers already computed (each paper is an expensive OpenAlex run)
        cur.execute("SELECT oaid FROM synthetic_field")
        done = {r[0] for r in cur.fetchall()}
    todo = [o for o in oaids if o not in done]
    print(f"computing synthetic field for {len(todo)} papers "
          f"({len(done)} already done)", flush=True)
    built = 0
    for i, oaid in enumerate(todo, 1):
        try:
            rec = synthetic_field(oaid)
        except requests.HTTPError as e:
            print(f"  [{i}] {oaid}: HTTP {e}", flush=True)
            continue
        if rec:
            _upsert(db, rec)   # fresh short-lived connection per upsert (Neon drops idle ones)
            built += 1
        if i % 25 == 0:
            print(f"  [{i}/{len(todo)}] built={built}", flush=True)
    print(f"done: {built} synthetic-field records this run")


def _target_oaids(conn, mode, per_community):
    with conn.cursor() as cur:
        if mode == "seed-and-leaders":
            cur.execute("SELECT DISTINCT work_oaid FROM author_works")
            oaids = {r[0] for r in cur.fetchall()}
            for sid in ("1803", "1802", "1800"):
                # Order by cited_by_count (stable; doesn't shift when percentiles are recomputed)
                # — these are the papers that sit at the top of the explore views.
                cur.execute(
                    """SELECT oaid FROM works
                       WHERE primary_subfield=%s AND cited_by_count IS NOT NULL
                       ORDER BY cited_by_count DESC LIMIT %s""",
                    (sid, per_community))
                oaids.update(r[0] for r in cur.fetchall())
            return sorted(oaids)
    return []


def _upsert(db, rec):
    import psycopg
    with psycopg.connect(db) as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO synthetic_field
                 (oaid,obs_percentile,p0,lam,n_refs,n_citers,weights,snapshot)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (oaid) DO UPDATE SET
                 obs_percentile=EXCLUDED.obs_percentile, p0=EXCLUDED.p0, lam=EXCLUDED.lam,
                 n_refs=EXCLUDED.n_refs, n_citers=EXCLUDED.n_citers, weights=EXCLUDED.weights,
                 snapshot=EXCLUDED.snapshot, computed_at=now()""",
            (rec["oaid"], rec["obs_percentile"], rec["p0"], rec["lam"], rec["n_refs"],
             rec["n_citers"], json.dumps(rec["weights"]), SNAPSHOT))
    # the connection context manager commits + closes on exit


if __name__ == "__main__":
    main()
