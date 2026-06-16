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

import _env
_env.load_env()  # load repo-root .env (secrets) before the os.environ reads below

API = "https://api.openalex.org/works"
MAILTO = os.environ.get("OPENALEX_MAILTO", "")
API_KEY = os.environ.get("OPENALEX_API_KEY", "")  # premium key: lifts the daily list budget
AS_OF = int(os.environ.get("AS_OF_YEAR", "2026"))
SNAPSHOT = os.environ.get("OPENALEX_SNAPSHOT", "openalex-dev")
UA = {"User-Agent": f"al-pipeline/1.0 ({MAILTO})"}

TAU = float(os.environ.get("H_HALFLIFE", "6")) / math.log(2)  # recency decay timescale
K_LAMBDA = float(os.environ.get("K_LAMBDA", "20"))
N_MIN_REFS = 5          # usable references below which the reference stage is skipped
MAX_CITERS = int(os.environ.get("MAX_CITERS", "300"))  # cap citing works scanned for the community
                        # mixture. 300 estimates the top-NEIGH_SIZE co-cited blend stably while
                        # bounding cost — high-cited papers were the runaway expense (each scanned
                        # page is a 200-record list query, the priciest OpenAlex call type).
NEIGH_SIZE = 200        # co-cited works kept for the community topic mixture
MAX_AUTHORS = 5         # cap the author-prior fan-out (one OpenAlex call per author)
AUTHOR_WORKS = 50       # recent works per author used to build the prior
TOPIC_ALPHA = 0.55      # blend weight on the paper's OWN topics vs the author prior

_COHORT = {}            # (subfield, year) -> {"total", "p0", "base"} cached cohort metadata

# --- OpenAlex spend safety. This backfill once ran up a ~$20 bill on the premium key (the
# highest-cited papers scan ~1000 citers each). It does NOT need premium — the free polite pool
# does the identical work — so main() defaults to polite and only spends on explicit --use-premium,
# with a --max-calls circuit breaker even then. ---
_N_CALLS = 0            # OpenAlex calls made this process
_CALL_CAP = 0           # 0 = unlimited; set to a positive cap by main() for premium runs


class CallCapReached(Exception):
    """Raised when a --use-premium run hits its --max-calls cap, to stop before billing more."""


def _get(params, tries=6):
    global _N_CALLS
    _N_CALLS += 1
    if _CALL_CAP and _N_CALLS > _CALL_CAP:
        raise CallCapReached(f"reached --max-calls={_CALL_CAP} OpenAlex-call cap (safety stop)")
    if MAILTO:
        params["mailto"] = MAILTO
    if API_KEY:
        params["api_key"] = API_KEY
    for attempt in range(tries):
        try:
            r = requests.get(API, params=params, timeout=60, headers=UA)
        except requests.exceptions.RequestException:
            time.sleep(min(30, 2 ** attempt))  # network timeout / reset -> retry
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(min(30, 2 ** attempt))  # back off on rate-limit / transient errors
            continue
        r.raise_for_status()
        return r.json()
    raise requests.exceptions.RequestException("OpenAlex retries exhausted")


def _sub(work):
    s = (((work.get("primary_topic") or {}).get("subfield") or {}).get("id") or "")
    return s.split("/")[-1] or None


def focal_meta(oaid):
    d = _get({"filter": f"ids.openalex:{oaid}",
              "select": "id,referenced_works,publication_year,cited_by_count,primary_topic,authorships,topics",
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


def cohort_meta(subfield, year):
    """Cached (total, p0, filter) for the (subfield, year) cohort. p0 is the exact zero-
    citation share (the uncited atom). Two count queries, cached per cohort."""
    key = (subfield, year)
    if key in _COHORT:
        return _COHORT[key]
    base = f"primary_topic.subfield.id:subfields/{subfield},publication_year:{year}"
    total = _get({"filter": base, "per-page": 1})["meta"]["count"]
    if not total:
        _COHORT[key] = {"total": 0, "p0": None, "base": base}
        return _COHORT[key]
    zero = _get({"filter": base + ",cited_by_count:0", "per-page": 1})["meta"]["count"]
    _COHORT[key] = {"total": total, "p0": zero / total, "base": base}
    time.sleep(0.1)
    return _COHORT[key]


def pct_in_cohort(subfield, year, cites):
    """Focal's EXACT full-population MID-RANK percentile (fraction in [0,1]) within the
    (subfield, year) cohort, plus that cohort's p0. No histogram, no cap, no sampling:
    the whole cohort (cited + uncited) is the denominator (QaL_spec.md §5). Ties — the
    uncited atom included — take the mid-rank via exact >cites / ==cites counts."""
    m = cohort_meta(subfield, year)
    if not m["total"]:
        return None, None
    if cites <= 0:
        return m["p0"] / 2.0, m["p0"]  # uncited atom sits at mid-rank 100·p0/2
    above = _get({"filter": m["base"] + f",cited_by_count:>{cites}", "per-page": 1})["meta"]["count"]
    at = _get({"filter": m["base"] + f",cited_by_count:{cites}", "per-page": 1})["meta"]["count"]
    below = m["total"] - above - at
    time.sleep(0.1)
    return (below + at / 2.0) / m["total"], m["p0"]


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


def author_prior_weights(w):
    """Weakest signal in the chain (QaL_spec §5): when a paper has neither a usable bibliography
    NOR citers, infer the community from CONTENT + AUTHORS — blend the paper's own OpenAlex topic
    mixture with the recency-weighted bodies of work of its authors (each normalized to unit mass
    so a prolific co-author doesn't swamp the others). Mirrors web/lib/synthetic.ts."""
    v = w.get("publication_year") or AS_OF
    # (a) content: the paper's own OpenAlex topics -> subfield distribution, weighted by score
    tm = defaultdict(float)
    for t in (w.get("topics") or []):
        sid = ((t.get("subfield") or {}).get("id") or "").split("/")[-1]
        if sid:
            tm[sid] += t.get("score") or 0.0
    # (b) author prior: each author's recency-weighted subfield mixture
    ids = []
    for a in (w.get("authorships") or []):
        aid = ((a.get("author") or {}).get("id") or "").split("/")[-1]
        if aid:
            ids.append(aid)
        if len(ids) >= MAX_AUTHORS:
            break
    am = defaultdict(float)
    for aid in ids:
        d = _get({"filter": f"author.id:{aid}", "select": "primary_topic,publication_year",
                  "per-page": AUTHOR_WORKS, "sort": "publication_year:desc"})
        per = defaultdict(float)
        for wk in (d.get("results") or []):
            sid = (((wk.get("primary_topic") or {}).get("subfield") or {}).get("id") or "").split("/")[-1]
            if not sid:
                continue
            g = math.exp(-max(0, v - (wk.get("publication_year") or v)) / TAU)
            per[sid] += g
        for sid, x in _normalize(per).items():  # unit mass per author
            am[sid] += x
        time.sleep(0.1)
    tm, am = _normalize(tm), _normalize(am)
    if not tm and not am:
        return {}
    alpha = TOPIC_ALPHA if (tm and am) else (1.0 if tm else 0.0)  # lean fully on whichever exists
    out = defaultdict(float)
    for sid, x in tm.items():
        out[sid] += alpha * x
    for sid, x in am.items():
        out[sid] += (1 - alpha) * x
    return dict(out)


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
        # author-prior fallback: content (own topics) + authors' bodies of work; the single-topic
        # focal subfield is only the very last resort if that yields nothing
        weights = author_prior_weights(w) or ({focal_sub: 1.0} if focal_sub else {})
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
    # Only rank against subfields carrying non-negligible weight (the rest contribute <~2%
    # to the blend); bounds the exact count queries without changing the percentile.
    keep = {s: w for s, w in weights.items() if w >= 0.02}
    if not keep:
        keep = weights
    r = p0 = wused = 0.0
    parts = []  # per-subfield {sid, weight, pct} — inputs to the blend-weighted calibration
    for s, ws in sorted(keep.items(), key=lambda x: -x[1]):
        pct, p0s = pct_in_cohort(s, v, cites)
        if pct is None:
            continue
        parts.append({"sid": s, "weight": ws, "pct": round(100 * pct, 2)})
        r += ws * pct
        p0 += ws * (p0s or 0.0)
        wused += ws
    if wused < 0.5:  # most weight had no cohort -> fallback to focal subfield
        pct, p0s = pct_in_cohort(focal_sub, v, cites)
        if pct is None:
            return None
        parts = [{"sid": focal_sub, "weight": 1.0, "pct": round(100 * pct, 2)}]
        r, p0, wused = pct, (p0s or 0.0), 1.0
    parts = [{"sid": p["sid"], "weight": round(p["weight"] / wused, 4), "pct": p["pct"]} for p in parts]

    return {
        "oaid": oaid,
        "obs_percentile": round(100 * r / wused, 2),
        "p0": round(p0 / wused, 4),
        "lam": None if lam is None else round(lam, 3),
        "n_refs": usable,
        "n_citers": n_citers,
        "weights": {s: round(ws, 3) for s, ws in sorted(weights.items(), key=lambda x: -x[1])[:8]},
        "parts": parts,
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
    ap.add_argument("--oaids-file", default="")  # newline-separated oaids (large backfills)
    ap.add_argument("--use-premium", action="store_true",
                    help="use the metered OpenAlex premium key; DEFAULT is the free polite pool "
                         "(backfills don't need premium and ran up a bill once)")
    ap.add_argument("--max-calls", type=int, default=3000,
                    help="safety cap on OpenAlex calls for a --use-premium run; stops cleanly when hit "
                         "(0 = unlimited)")
    args = ap.parse_args()

    global API_KEY, _CALL_CAP
    if args.use_premium:
        _CALL_CAP = max(0, args.max_calls)
        print(f"OpenAlex: PREMIUM key (metered) — safety cap {_CALL_CAP or 'none'} calls.", flush=True)
    else:
        API_KEY = ""  # free polite pool by default — a backfill must never silently bill
        print("OpenAlex: free polite pool (default). Pass --use-premium to use the metered key.", flush=True)

    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL not set")
    import psycopg
    with psycopg.connect(db) as c0, c0.cursor() as cur:
        if args.oaids_file:
            with open(args.oaids_file) as f:
                oaids = [ln.strip() for ln in f if ln.strip()]
        elif args.oaids:
            oaids = [s.strip() for s in args.oaids.split(",") if s.strip()]
        else:
            oaids = _target_oaids(c0, args.targets, args.per_community)
        # resume: skip papers already computed WITH the per-subfield parts (so a re-run backfills
        # parts for rows computed before the blend-weighted calibration existed).
        cur.execute("SELECT oaid FROM synthetic_field WHERE parts IS NOT NULL")
        done = {r[0] for r in cur.fetchall()}
    todo = [o for o in oaids if o not in done]
    print(f"computing synthetic field for {len(todo)} papers "
          f"({len(done)} already done)", flush=True)
    built = 0
    for i, oaid in enumerate(todo, 1):
        try:
            rec = synthetic_field(oaid)
        except CallCapReached as e:
            print(f"  [{i}] stopping cleanly: {e} (built {built} this run; rerun to resume)", flush=True)
            break
        except requests.exceptions.RequestException as e:
            print(f"  [{i}] {oaid}: skipped ({str(e)[:50]})", flush=True)
            continue
        if rec:
            _upsert(db, rec)   # fresh short-lived connection per upsert (Neon drops idle ones)
            built += 1
        if i % 25 == 0:
            print(f"  [{i}/{len(todo)}] built={built}", flush=True)
    print(f"done: {built} synthetic-field records this run")


def _target_oaids(conn, mode, per_community):
    with conn.cursor() as cur:
        if mode == "faculty":
            import yaml
            ids = [str(v) for v in (yaml.safe_load(open("pipeline/oid_faculty_ids.yml")) or {}).values() if v]
            cur.execute("SELECT DISTINCT work_oaid FROM author_works WHERE author_oaid = ANY(%s)", (ids,))
            return sorted({r[0] for r in cur.fetchall()})
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
                 (oaid,obs_percentile,p0,lam,n_refs,n_citers,weights,parts,snapshot)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (oaid) DO UPDATE SET
                 obs_percentile=EXCLUDED.obs_percentile, p0=EXCLUDED.p0, lam=EXCLUDED.lam,
                 n_refs=EXCLUDED.n_refs, n_citers=EXCLUDED.n_citers, weights=EXCLUDED.weights,
                 parts=EXCLUDED.parts, snapshot=EXCLUDED.snapshot, computed_at=now()""",
            (rec["oaid"], rec["obs_percentile"], rec["p0"], rec["lam"], rec["n_refs"],
             rec["n_citers"], json.dumps(rec["weights"]), json.dumps(rec.get("parts")), SNAPSHOT))
    # the connection context manager commits + closes on exit


if __name__ == "__main__":
    main()
