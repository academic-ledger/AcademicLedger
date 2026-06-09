"""Stage-one calibration coverage for the OID department (QaL_spec.md §11, "Coverage rollout
via staged sampling"). Resumable and budget-aware. Goal by morning: broad, honestly-labeled
coverage of the department's subfields — not perfection.

Budget order (cheap -> expensive; each step resumable, each unit checkpointed):
  STEP 1  footprint   — resolve OID faculty -> OpenAlex authors; tally their subfields ->
                        data/oid_footprint.json + the ranked target set (90%/95% marks). Small.
  STEP 2  skeleton    — per target (subfield x vintage): an EXACT coarse CDF from one
                        group_by=cited_by_count histogram + a few tail count-queries. Covers the
                        whole head immediately and is quota-light. source='skeleton'.
  STEP 3  refine      — per cohort: a UNIFORM RANDOM sample (1k) fills the interior CDF
                        (source='sampled'); per subfield, HYBRID calibration — the proven
                        nonparametric fit (calib_lib) where matured data allows, the parametric
                        fallback (calib_parametric, §7 shrinkage) otherwise — writes
                        calibration_models with a confidence tier. Heaviest; runs as budget allows.

Confidence tiers (never gate-passed without the back-test):
  parametric < fitted < gate-passed. Only gate-passed is shown as a forecast (compute_qal/UI).
The seed (1803/1802/1800) is already gate-passed and is excluded from Steps 2/3 (never downgraded).

On HTTP 429 / daily-budget exhaustion: checkpoint, print the coverage report, and exit 0 cleanly
so the launchd resume continues after the budget resets. Re-running skips finished units.

Usage:  DATABASE_URL=... OPENALEX_MAILTO=... python pipeline/coverage_rollout.py [--steps 123]
Env:    OPENALEX_SNAPSHOT (base label, default 'rollout-YYYY-MM'), AS_OF_YEAR (2026),
        H_LONG_HORIZON (10), SAMPLE_N (1000), MAX_REQUESTS (safety cap, optional),
        COVER_TO (cumulative footprint share to target, default 0.95).
"""
import os
import sys
import json
import time
import argparse
from collections import defaultdict

import requests
import numpy as np

import calib_lib as cl
import calib_parametric as cp
import build_percentiles as bp
import pull_cohort as pc

API = "https://api.openalex.org"
MAILTO = os.environ.get("OPENALEX_MAILTO", "")
API_KEY = os.environ.get("OPENALEX_API_KEY", "")  # premium key: lifts the daily list budget
UA = {"User-Agent": f"al-pipeline/1.0 ({MAILTO})"}
AS_OF = int(os.environ.get("AS_OF_YEAR", "2026"))
H = int(os.environ.get("H_LONG_HORIZON", "10"))
SAMPLE_N = int(os.environ.get("SAMPLE_N", "1000"))   # light score-year sample, for serving only
CALIB_N = int(os.environ.get("CALIB_N", "10000"))    # DEEP matured-cohort pull, for calibration
COVER_TO = float(os.environ.get("COVER_TO", "0.95"))
MAX_REQUESTS = int(os.environ.get("MAX_REQUESTS", "0")) or None
SNAP = os.environ.get("OPENALEX_SNAPSHOT", "rollout-2026-06")
# Snapshots are stage-numbered so the existing `snapshot DESC` read prefers sampled over skeleton.
SNAP_SKEL = f"{SNAP}-1skeleton"
SNAP_SAMP = f"{SNAP}-2sampled"
MODEL_VERSION = os.environ.get("MODEL_VERSION", "qal-0.1")
SEED = {"1803", "1802", "1800"}

# OID standing faculty (surnames). Resolved to OpenAlex authors, Penn-preferred, topic-disambiguated.
FACULTY = ["Allon", "Bastani", "Cachon", "Duckworth", "Gallino", "Gans", "Harker", "Hitt",
           "Hosanagar", "Kimbrough", "Knox", "Milkman", "Netessine", "Rock", "Santoro", "Savin",
           "Schweitzer", "Sharma", "Simmons", "Smitizsky", "Song", "Su", "Sungu", "Tambe",
           "Terwiesch", "Ulrich", "Veeraraghavan", "Watts", "Wu", "Yu"]

# Fields/domains an OID scholar plausibly publishes in (OM, IS, marketing/behavioral, networks),
# used only to disambiguate a Penn namesake — the footprint itself is the union of their subfields.
OID_FIELDS = {"Decision Sciences", "Business, Management and Accounting",
              "Economics, Econometrics and Finance", "Psychology", "Social Sciences",
              "Computer Science"}

SCORE_YEARS = list(range(2016, AS_OF + 1))     # vintages we display QaL for
MATURE_YEARS = list(range(2008, 2017))         # matured vintages we calibrate on
ALL_VINTAGES = sorted(set(SCORE_YEARS + MATURE_YEARS))


class BudgetExhausted(Exception):
    """OpenAlex daily budget / rate limit hit — stop cleanly and let the resume continue."""


_req_count = 0
_last_remaining_usd = None


def GET(path, **params):
    """Budget-aware GET. Raises BudgetExhausted on a budget-429 (clean stop); retries transient
    429/5xx a few times. Tracks request count and any reported remaining daily budget."""
    global _req_count, _last_remaining_usd
    if MAX_REQUESTS and _req_count >= MAX_REQUESTS:
        raise BudgetExhausted(f"hit local MAX_REQUESTS cap ({MAX_REQUESTS})")
    if MAILTO:
        params["mailto"] = MAILTO
    if API_KEY:
        params["api_key"] = API_KEY
    url = f"{API}/{path.lstrip('/')}"
    for attempt in range(5):
        _req_count += 1
        r = requests.get(url, params=params, headers=UA, timeout=60)
        if r.status_code == 429:
            body = {}
            try:
                body = r.json()
            except Exception:
                pass
            # A budget/credit exhaustion is terminal for today; a transient throttle is retryable.
            rem = body.get("dailyRemainingUsd")
            if rem is not None:
                _last_remaining_usd = rem
            msg = (body.get("message", "") + body.get("error", "")).lower()
            if rem == 0 or "insufficient" in msg or "budget" in msg:
                raise BudgetExhausted(body.get("message") or "OpenAlex budget exhausted")
            time.sleep(min(30, 2 ** attempt))
            continue
        if r.status_code >= 500:
            time.sleep(min(30, 2 ** attempt))
            continue
        r.raise_for_status()
        return r.json()
    raise BudgetExhausted("repeated 429/5xx after retries — treating as exhausted")


# ----- checkpoint helpers (coverage_progress) -------------------------------------------------

def cp_get_done(conn, step):
    with conn.cursor() as cur:
        cur.execute("SELECT subfield, vintage FROM coverage_progress WHERE step=%s AND status='done'",
                    (step,))
        return {(s, v) for s, v in cur.fetchall()}


def cp_mark(conn, step, subfield, vintage, status, confidence=None, detail=None):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO coverage_progress (step,subfield,vintage,status,confidence,detail,updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,now())
               ON CONFLICT (step,subfield,vintage) DO UPDATE SET
                 status=EXCLUDED.status, confidence=EXCLUDED.confidence,
                 detail=EXCLUDED.detail, updated_at=now()""",
            (step, subfield or "", vintage or 0, status, confidence,
             json.dumps(detail) if detail is not None else None))
    conn.commit()


# ----- STEP 1: OID footprint ------------------------------------------------------------------

def _penn_id():
    d = GET("/institutions", search="University of Pennsylvania", per_page=1,
            select="id,display_name")
    res = d.get("results") or []
    return res[0]["id"].split("/")[-1] if res else None


def _oid_score(author):
    topics = author.get("topics") or []
    tot = sum(t.get("count", 0) for t in topics) or 1
    hit = sum(t.get("count", 0) for t in topics
              if ((t.get("field") or {}).get("display_name") in OID_FIELDS))
    return hit / tot


def _load_overrides():
    """Verified surname -> OpenAlex author id (pipeline/oid_faculty_ids.yml). Preferred over the
    name resolver, which mis-IDs common surnames."""
    try:
        import yaml
        m = yaml.safe_load(open("pipeline/oid_faculty_ids.yml")) or {}
        return {str(k): str(v) for k, v in m.items() if v}
    except Exception:
        return {}


OVERRIDES = _load_overrides()


def resolve_author(surname, penn_id):
    sel = "id,display_name,works_count,cited_by_count,last_known_institutions,topics"
    aid = OVERRIDES.get(surname)
    if aid:
        try:
            a = GET(f"/authors/{aid}", select=sel)
            return {"surname": surname, "oaid": a["id"].split("/")[-1],
                    "name": a.get("display_name"), "works": a.get("works_count"),
                    "cites": a.get("cited_by_count"), "topics": a.get("topics") or [],
                    "oid_score": round(_oid_score(a), 3), "confidence": "override",
                    "source": "override", "n_candidates": 1}
        except BudgetExhausted:
            raise
        except Exception:
            pass  # bad id / fetch error -> fall through to name search
    src = "penn"
    d = GET("/authors", search=surname, per_page=25, select=sel,
            filter=f"last_known_institutions.id:{penn_id}") if penn_id else {"results": []}
    cands = d.get("results") or []
    if not cands:
        src = "global"
        cands = (GET("/authors", search=surname, per_page=25, select=sel).get("results") or [])
    if not cands:
        return None
    cands.sort(key=lambda a: (_oid_score(a), a.get("cited_by_count", 0)), reverse=True)
    best = cands[0]
    score = _oid_score(best)
    conf = "high" if (src == "penn" and score >= 0.25) else \
           "medium" if score >= 0.15 else "low"
    return {"surname": surname, "oaid": best["id"].split("/")[-1],
            "name": best.get("display_name"), "works": best.get("works_count"),
            "cites": best.get("cited_by_count"), "topics": best.get("topics") or [],
            "oid_score": round(score, 3), "confidence": conf, "source": src,
            "n_candidates": len(cands)}


def step1_footprint(conn):
    print("STEP 1 — OID footprint", flush=True)
    penn = _penn_id()
    print(f"  Penn institution id: {penn}", flush=True)
    resolved, names = [], {}
    sub_share = defaultdict(float)  # department subfield share (per-faculty-normalized, equal weight)
    for s in FACULTY:
        a = resolve_author(s, penn)
        if not a:
            print(f"  {s:16s} -> NOT FOUND", flush=True)
            continue
        resolved.append(a)
        by_sub = defaultdict(float)
        for t in a["topics"]:
            sub = (t.get("subfield") or {})
            sid = (sub.get("id") or "").split("/")[-1]
            if sid:
                by_sub[sid] += t.get("count", 0)
                names[sid] = sub.get("display_name")
        tot = sum(by_sub.values()) or 1
        for sid, c in by_sub.items():
            sub_share[sid] += c / tot          # each faculty contributes equal total weight
        flag = "" if a["confidence"] in ("high", "override") else f"  <-- {a['confidence']} confidence, review"
        print(f"  {s:16s} -> {a['name']} ({a['oaid']}) "
              f"oid={a['oid_score']} {a['source']}{flag}", flush=True)

    nf = len(resolved) or 1
    ranked = sorted(((sid, sh / nf, names.get(sid)) for sid, sh in sub_share.items()),
                    key=lambda x: -x[1])
    rows, cum, mark90, mark95 = [], 0.0, None, None
    for sid, share, name in ranked:
        cum += share
        rows.append({"sid": sid, "name": name, "share": round(share, 4),
                     "cumulative": round(cum, 4), "is_seed": sid in SEED})
        if mark90 is None and cum >= 0.90:
            mark90 = sid
        if mark95 is None and cum >= 0.95:
            mark95 = sid
    total = cum or 1.0
    for r in rows:                       # renormalize cumulative to 1.0 (topics don't cover 100%)
        r["cumulative"] = round(r["cumulative"] / total, 4)

    footprint = {
        "as_of": AS_OF, "n_faculty_resolved": len(resolved), "n_faculty_total": len(FACULTY),
        "cover_90_at_subfield": mark90, "cover_95_at_subfield": mark95,
        "subfields": rows,
        "resolution": [{k: a[k] for k in ("surname", "oaid", "name", "works", "cites",
                                          "oid_score", "confidence", "source", "n_candidates")}
                       for a in resolved],
    }
    os.makedirs("data", exist_ok=True)
    with open("data/oid_footprint.json", "w") as f:
        json.dump(footprint, f, indent=2)
    # persist subfield names (bonus: fills the UI composition/labels, no extra OpenAlex calls)
    with conn.cursor() as cur:
        for sid, nm in names.items():
            if nm:
                cur.execute("INSERT INTO subfields (id,name) VALUES (%s,%s) "
                            "ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name", (sid, nm))
    conn.commit()
    cp_mark(conn, "footprint", "", 0, "done",
            detail={"resolved": len(resolved), "cover90": mark90, "cover95": mark95,
                    "low_conf": [a["surname"] for a in resolved if a["confidence"] != "high"]})

    # target set = ranked NON-seed subfields up to COVER_TO cumulative (the head, seed excluded)
    targets = [r["sid"] for r in rows if not r["is_seed"] and r["cumulative"] <= COVER_TO]
    if not targets:
        targets = [r["sid"] for r in rows if not r["is_seed"]][:10]
    print(f"  footprint: {len(rows)} subfields; head to {COVER_TO:.0%} = {len(targets)} non-seed "
          f"targets; 90% at {mark90}, 95% at {mark95}", flush=True)
    print(f"  wrote data/oid_footprint.json", flush=True)
    return targets


# ----- STEP 2: skeleton percentile tables -----------------------------------------------------

TAIL_LADDER = [10, 25, 50, 100, 250, 500, 1000]


def skeleton_cdf(n, hist, tail_counts):
    """Coarse exact mid-rank CDF from a head histogram {cites:count} (group_by) plus tail
    thresholds {X: #works with cites > X}. Returns (n, [{cites,pct}]) like build_percentiles."""
    bps = []
    heads = sorted(hist)
    below = 0
    for v in heads:
        c = hist[v]
        pct = 100.0 * (below + c / 2.0) / n
        bps.append({"cites": int(v), "pct": round(pct, 3)})
        below += c
    for X in sorted(tail_counts):
        above = tail_counts[X]
        pct = 100.0 * (n - above) / n          # share at or below X
        bps.append({"cites": int(X), "pct": round(pct, 3)})
    # sort, dedupe by cites (keep the max pct), enforce monotonic non-decreasing
    by_c = {}
    for b in bps:
        by_c[b["cites"]] = max(by_c.get(b["cites"], 0.0), b["pct"])
    out, run = [], 0.0
    for cites in sorted(by_c):
        run = max(run, min(100.0, by_c[cites]))
        out.append({"cites": cites, "pct": round(run, 3)})
    return out


def step2_skeletons(conn, targets):
    print("STEP 2 — skeleton percentile tables", flush=True)
    done = cp_get_done(conn, "skeleton")
    for sid in targets:
        for v in ALL_VINTAGES:
            if (sid, v) in done:
                continue
            base = f"primary_topic.subfield.id:subfields/{sid},publication_year:{v}"
            d = GET("/works", filter=base, group_by="cited_by_count", per_page=200)
            n = d.get("meta", {}).get("count", 0)
            if not n:
                cp_mark(conn, "skeleton", sid, v, "empty")
                continue
            hist = {}
            for g in d.get("group_by", []):
                try:
                    hist[int(g["key"])] = g["count"]
                except (ValueError, TypeError):
                    continue
            tail = {}
            for X in TAIL_LADDER:
                a = GET("/works", filter=base + f",cited_by_count:>{X}", per_page=1)
                tail[X] = a.get("meta", {}).get("count", 0)
                if tail[X] == 0:
                    break                       # nothing above X => higher thresholds are 0 too
            cdf = skeleton_cdf(n, hist, tail)
            p0 = hist.get(0, 0) / n
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO cohort_percentiles (subfield,publication_year,n,cdf,snapshot,source)
                       VALUES (%s,%s,%s,%s,%s,'skeleton')
                       ON CONFLICT (subfield,publication_year,snapshot)
                       DO UPDATE SET n=EXCLUDED.n, cdf=EXCLUDED.cdf, source='skeleton'""",
                    (sid, v, n, json.dumps(cdf), SNAP_SKEL))
            conn.commit()
            cp_mark(conn, "skeleton", sid, v, "done",
                    detail={"n": n, "p0": round(p0, 4), "breakpoints": len(cdf)})
        print(f"  {sid}: skeletons across {len(ALL_VINTAGES)} vintages", flush=True)


# ----- STEP 3: deep in-memory calibration + light serving sample ------------------------------
# Budget is no longer the constraint, so this step is restructured for QUALITY:
#   * Percentiles stay EXACT (the Step-2 skeletons); they are NOT superseded by sampled CDFs.
#   * Calibration pulls the matured cohorts DEEPLY (~CALIB_N, the seed's proven depth) and holds
#     them IN MEMORY only — fit-and-discard, so Neon doesn't bloat (the M10 discipline) — which
#     lets subfields actually reach the back-test gate (gate-passed) instead of the parametric tier.
#   * A light score-year sample is stored to `works` ONLY so the subfield's papers appear in the
#     served explore list; their percentile still comes from the exact skeleton, not the sample.

def _pull_cohort_mem(sid, v, n):
    """Up to n works of a cohort, uniform-random, held IN MEMORY (never stored): [(cites, cby)]."""
    try:
        rows = pc.fetch_cohort(sid, v, sample=n, seed=42)
        return [(r["cited_by_count"] or 0, r["counts_by_year"] or {}) for r in rows]
    except requests.HTTPError as e:
        if "429" in str(e):
            raise BudgetExhausted("matured-cohort pull hit 429")
        raise


def _store_serving_sample(conn, sid, v, n):
    """Store a light score-year sample to `works` so the subfield's papers are served in explore
    (percentile comes from the exact skeleton, not this sample). Returns the row count."""
    try:
        rows = list(pc.fetch_cohort(sid, v, sample=n, seed=42))
    except requests.HTTPError as e:
        if "429" in str(e):
            raise BudgetExhausted("serving-sample pull hit 429")
        raise
    if rows:
        pc.upsert(conn, rows)
    return len(rows)


def _write_calib_cells(conn, sid, cells, confidence):
    """Persist calibration cells {(age,grid_pt): cell} for a community + confidence tier."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM calibration_models WHERE community=%s AND model_version=%s",
                    (sid, MODEL_VERSION))
        for (age, g), c in cells.items():
            cur.execute(
                """INSERT INTO calibration_models
                     (community,age_years,obs_pct_bin,eventual_median,ci_lo,ci_hi,
                      p_ge50,p_ge75,p_ge90,p_ge95,p_ge99,n_train,model_version,confidence)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (community,age_years,obs_pct_bin,model_version) DO UPDATE SET
                     eventual_median=EXCLUDED.eventual_median, ci_lo=EXCLUDED.ci_lo,
                     ci_hi=EXCLUDED.ci_hi, p_ge50=EXCLUDED.p_ge50, p_ge75=EXCLUDED.p_ge75,
                     p_ge90=EXCLUDED.p_ge90, p_ge95=EXCLUDED.p_ge95, p_ge99=EXCLUDED.p_ge99,
                     n_train=EXCLUDED.n_train, confidence=EXCLUDED.confidence""",
                (sid, age, round(g, 3), round(c["median"], 3), round(c["q5"], 3),
                 round(c["q95"], 3), round(c["p_ge50"], 4), round(c["p_ge75"], 4),
                 round(c["p_ge90"], 4), round(c["p_ge95"], 4), round(c["p_ge99"], 4),
                 int(c.get("n", 0)), MODEL_VERSION, confidence))
    conn.commit()


def _calibrate_subfield(conn, sid):
    """Hybrid calibration for one subfield from DEEP in-memory matured cohorts. Nonparametric
    (calib_lib) + LOVO back-test where >=3 matured vintages have data -> fitted/gate-passed;
    parametric fallback (calib_parametric §7) otherwise. The pulled works are never persisted."""
    prepared, used_vintages, allrows = {}, [], []
    for v in MATURE_YEARS:
        rows = _pull_cohort_mem(sid, v, CALIB_N)
        cp_mark(conn, "sample", sid, v, "done" if rows else "empty", detail={"n": len(rows)})
        allrows.extend({"cites": c, "counts_by_year": cby, "vintage": v} for c, cby in rows)
        if len(rows) >= 50:
            prepared[v] = cl.prepare([cby for _, cby in rows], v, H)
            used_vintages.append(v)

    if len(used_vintages) >= 3:
        # nonparametric fit on the matured vintages, conformally widened, then back-tested.
        cells = cl.fit_cells(prepared, used_vintages, H)
        cov = _backtest_coverage(prepared, used_vintages)
        Q = cl.conformal_q(prepared, used_vintages[:-1], used_vintages[-1:], H)
        for (a, g), c in cells.items():
            lo, hi = cl.predict_interval(c, Q.get(a, 0.0))
            c["q5"], c["q95"] = lo, hi
        # Asymmetric gate. The danger is UNDER-coverage (overconfident intervals), so the floor is
        # firm at 0.88 (~the seed's 0.90 target). Mild OVER-coverage just means slightly wide,
        # conservative intervals — safe and on-brand ("decide late, honest uncertainty") — so the
        # ceiling is generous (0.97); only gross over-widening is rejected. Single-subfield conformal
        # runs a touch wider than the pooled seed. Below the floor -> 'fitted' (pending), no forecast.
        confidence = "gate-passed" if (cov is not None and 0.88 <= cov <= 0.97) else "fitted"
        _write_calib_cells(conn, sid, cells, confidence)
        return confidence, {"vintages": len(used_vintages),
                            "coverage": round(cov, 3) if cov is not None else None,
                            "n_train": len(allrows)}

    # parametric fallback: fit (half_life, tail) from whatever matured data we got, shrunk to prior.
    if len(allrows) >= 50:
        params = cp.fit_params(allrows)
        cells = {(a, g): cp.cell(a, g, params, H) for a in range(1, H) for g in cl.GRID}
        _write_calib_cells(conn, sid, cells, "parametric")
        return "parametric", {"params": params, "samples": len(allrows)}
    return None, {"reason": "insufficient matured data"}


def _backtest_coverage(prepared, vintages):
    """Leave-one-vintage-out 90%-interval coverage across the matured vintages (the gate)."""
    if len(vintages) < 3:
        return None
    hits = tot = 0
    for held in vintages:
        fit_v = [v for v in vintages if v != held]
        cells = cl.fit_cells(prepared, fit_v, H)
        Q = cl.conformal_q(prepared, fit_v[:-1], fit_v[-1:], H) if len(fit_v) >= 2 else {}
        pa = prepared[held]
        for a in range(1, H):
            obs_pct, eve_pct = pa[a]
            for op, y in zip(obs_pct, eve_pct):
                cell = cl.predict_cell(cells, a, op)
                if cell is None:
                    continue
                lo, hi = cl.predict_interval(cell, Q.get(a, 0.0))
                hits += int(lo <= y <= hi)
                tot += 1
    return hits / tot if tot else None


def step3_calibrate(conn, targets):
    print("STEP 3 — deep matured-cohort calibration (in-memory) + light serving sample", flush=True)
    calib_done = cp_get_done(conn, "calibrate")
    serve_done = cp_get_done(conn, "serve")
    for sid in targets:
        # calibration is atomic per subfield (the matured cohorts must be fit together), so on
        # resume an interrupted subfield re-pulls; finished subfields are skipped.
        if (sid, 0) not in calib_done:
            conf, detail = _calibrate_subfield(conn, sid)
            cp_mark(conn, "calibrate", sid, 0, "done" if conf else "empty",
                    confidence=conf, detail=detail)
            print(f"  {sid}: calibration -> {conf} {detail}", flush=True)
        # light score-year serving sample so the subfield's papers appear in the explore cache
        # (resumable per vintage; percentile comes from the exact skeleton, not this sample).
        for v in SCORE_YEARS:
            if (sid, v) in serve_done:
                continue
            k = _store_serving_sample(conn, sid, v, SAMPLE_N)
            cp_mark(conn, "serve", sid, v, "done" if k else "empty", detail={"n": k})


# ----- coverage report ------------------------------------------------------------------------

def report(conn):
    print("\n===== COVERAGE REPORT =====", flush=True)
    with conn.cursor() as cur:
        cur.execute("SELECT status,count(*) FROM coverage_progress WHERE step='skeleton' GROUP BY 1")
        print("skeleton cohorts (exact percentiles):", dict(cur.fetchall()))
        cur.execute("SELECT status,count(*) FROM coverage_progress WHERE step='serve' GROUP BY 1")
        print("serving samples (score-year):", dict(cur.fetchall()))
        cur.execute("SELECT confidence,count(*) FROM coverage_progress WHERE step='calibrate' "
                    "AND status='done' GROUP BY 1")
        print("calibrated subfields by tier:", dict(cur.fetchall()))
        cur.execute("SELECT confidence,count(DISTINCT community) FROM calibration_models GROUP BY 1")
        print("calibration_models communities by tier:", dict(cur.fetchall()))
        cur.execute("SELECT subfield,vintage FROM coverage_progress WHERE status='error' LIMIT 20")
        errs = cur.fetchall()
        if errs:
            print("errors:", errs)
    print(f"requests this run: {_req_count}"
          + (f"; OpenAlex dailyRemainingUsd~{_last_remaining_usd}" if _last_remaining_usd is not None else ""),
          flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default="123", help="which steps to run, e.g. '12' or '3'")
    ap.add_argument("--targets", default="", help="comma-separated subfield ids (skip footprint targeting)")
    args = ap.parse_args()
    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL not set")
    import psycopg
    conn = psycopg.connect(db)
    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    try:
        if "1" in args.steps:
            t = step1_footprint(conn)
            if not targets:
                targets = t
        if not targets:  # resume case: rebuild target set from the persisted footprint
            try:
                fp = json.load(open("data/oid_footprint.json"))
                targets = [r["sid"] for r in fp["subfields"]
                           if not r["is_seed"] and r["cumulative"] <= COVER_TO]
            except Exception:
                targets = []
        targets = [t for t in targets if t not in SEED]
        if "2" in args.steps:
            step2_skeletons(conn, targets)
        if "3" in args.steps:
            step3_calibrate(conn, targets)
        print("\nrollout complete (all requested steps finished within budget).", flush=True)
    except BudgetExhausted as e:
        print(f"\n[budget] stopping cleanly: {e}", flush=True)
    finally:
        report(conn)
        conn.close()


if __name__ == "__main__":
    main()
