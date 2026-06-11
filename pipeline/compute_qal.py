"""Compose served QaL records: works + cohort_percentiles + calibration_models -> qal_records.

For each work:
  - Layer A (universal): observed percentile = empirical-CDF lookup of cited_by_count
    within its (subfield, year) cohort. Always present when the cohort has a percentile table.
  - Layer B (scope-bound): if the work's community is calibrated, attach the posterior over
    eventual percentile (point = median, 90% interval = [5th, 95th], class_prob = mass above
    each NSF cut) for its (community, age, observed-pct bin). Else -> calibration-pending.

Works whose cohort has no percentile table are skipped (left untouched), so partial runs
don't clobber existing records. Vercel only reads this table; all the math lives here.

Usage:  DATABASE_URL=... python pipeline/compute_qal.py
Env:    OPENALEX_SNAPSHOT (cohort snapshot to read), AS_OF_YEAR (scoring year, default 2026),
        MODEL_VERSION (calibration model_version, default qal-0.1)
"""
import os
import json
import bisect
import math

import _env
_env.load_env()  # load repo-root .env (secrets) before any os.environ.get below

import calib_lib as cl

CUTS = [50, 75, 90, 95, 99]


def _class_prob(point, lo, hi):
    """NSF cumulative class probabilities P(eventual >= cut) from a normal centered at the point
    with sd implied by the 90% interval (mirrors web/lib/qal.ts classProb, floor 1.5)."""
    sd = max(1.5, (hi - lo) / 3.2897)  # 90% interval ~= +/- 1.6449 sd
    sf = lambda k: 0.5 * math.erfc((k - point) / (sd * math.sqrt(2)))
    return {f"ge{c}": round(min(1.0, max(0.0, sf(c))), 4) for c in CUTS}


def load_labels():
    """subfield id -> human label, from cohorts.yml (seed + extensions)."""
    try:
        import yaml
        cfg = yaml.safe_load(open("pipeline/cohorts.yml"))
    except Exception:
        return {}, 10, []
    labels = {}
    for key in ("seed_subfields", "extension_subfields"):
        labels.update({str(k): v for k, v in (cfg.get(key) or {}).items()})
    seed = [str(k) for k in (cfg.get("seed_subfields") or {})]
    return labels, cfg.get("long_horizon_years", 10), seed


def obs_percentile(cdf, cites):
    """Empirical-CDF lookup: percentile = share of the cohort at or below `cites`.
    cdf is [{"cites": c, "pct": p}, ...] sorted ascending by cites (a step function)."""
    xs = [b["cites"] for b in cdf]
    i = bisect.bisect_right(xs, cites) - 1
    if i < 0:
        return 0.0
    return float(cdf[i]["pct"])


def main():
    db = os.environ.get("DATABASE_URL")
    if not db:
        print("No DATABASE_URL; this job expects the datastore. See README.")
        return
    import psycopg

    labels, H, seed = load_labels()
    snapshot = os.environ.get("OPENALEX_SNAPSHOT")  # None -> pick latest per cohort
    as_of = int(os.environ.get("AS_OF_YEAR", "2026"))
    model_version = os.environ.get("MODEL_VERSION", "qal-0.1")

    conn = psycopg.connect(db, keepalives=1, keepalives_idle=30,
                           keepalives_interval=10, keepalives_count=5)
    n_written = 0
    n_calibrated = 0
    with conn.cursor() as cur:
        # Preload the LATEST cohort percentile table per (subfield, year): {(sid, year): (n, cdf)}.
        # We always read latest-per-cohort by lexical-max snapshot, NOT an exact-snapshot filter:
        # snapshots are stage-suffixed (e.g. 'rollout-2026-06-1skeleton' < '-2sampled', so sampled
        # supersedes skeleton) and the seed uses a different prefix ('openalex-...'), so an exact
        # OPENALEX_SNAPSHOT match (e.g. 'rollout-2026-06') would match nothing. OPENALEX_SNAPSHOT is
        # only the data_snapshot LABEL on written records, never a read filter.
        cur.execute(
            """SELECT DISTINCT ON (subfield, publication_year)
                      subfield, publication_year, n, cdf
                 FROM cohort_percentiles
                 ORDER BY subfield, publication_year, snapshot DESC"""
        )
        cohorts = {(r[0], r[1]): (r[2], r[3]) for r in cur.fetchall()}
        if not cohorts:
            print("No cohort_percentiles found; run build_percentiles first.")
            conn.close()
            return

        # Preload calibration grid cells per community: {community: {(age, grid_pt): cell}}.
        # The conditioning on observed percentile is continuous — predict_cell interpolates
        # between grid points — so a paper at 99.97 is conditioned on ~99.97, not "top decile".
        # ci_lo/ci_hi are already the conformally-widened interval; map them to q5/q95.
        cur.execute(
            """SELECT community, age_years, obs_pct_bin, eventual_median, ci_lo, ci_hi,
                      p_ge50, p_ge75, p_ge90, p_ge95, p_ge99, confidence
                 FROM calibration_models WHERE model_version=%s""",
            (model_version,),
        )
        calib_by_comm = {}
        confidence_by_comm = {}  # community -> tier (parametric|fitted|gate-passed)
        for r in cur.fetchall():
            calib_by_comm.setdefault(r[0], {})[(r[1], float(r[2]))] = dict(
                median=float(r[3]), q5=float(r[4]), q95=float(r[5]), n=1,
                p_ge50=float(r[6]), p_ge75=float(r[7]), p_ge90=float(r[8]),
                p_ge95=float(r[9]), p_ge99=float(r[10]),
            )
            confidence_by_comm[r[0]] = r[11]

        # Preload the cached synthetic field — the OFFICIAL reference class where available
        # (QaL_spec.md §5). {oaid: (n_citers, synthetic_percentile)}.
        cur.execute("SELECT oaid, n_citers, obs_percentile, parts FROM synthetic_field")
        synth = {r[0]: (r[1], float(r[2]), r[3]) for r in cur.fetchall()}

        # Walk every work whose cohort we have a percentile table for. Pull the display fields
        # too so qal_records is self-sufficient for serving (the cache; works is just staging).
        cur.execute(
            "SELECT oaid, primary_subfield, publication_year, cited_by_count, title, doi, "
            "       primary_field, is_oa, is_retracted, raw->>'authors', raw->>'venue', "
            "       raw->>'subfield_label', raw->'authorships' "
            "FROM works WHERE primary_subfield IS NOT NULL AND publication_year IS NOT NULL"
        )
        rows = cur.fetchall()

    UPSERT = """INSERT INTO qal_records
                 (oaid, reference_class, obs_percentile, calibrated,
                  qal_point, qal_ci_lo, qal_ci_hi, class_prob, metrics, display,
                  method_version, data_snapshot)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (oaid) DO UPDATE SET
                 reference_class=EXCLUDED.reference_class, obs_percentile=EXCLUDED.obs_percentile,
                 calibrated=EXCLUDED.calibrated, qal_point=EXCLUDED.qal_point,
                 qal_ci_lo=EXCLUDED.qal_ci_lo, qal_ci_hi=EXCLUDED.qal_ci_hi,
                 class_prob=EXCLUDED.class_prob, metrics=EXCLUDED.metrics, display=EXCLUDED.display,
                 method_version=EXCLUDED.method_version,
                 data_snapshot=EXCLUDED.data_snapshot, computed_at=now()"""
    batch = []

    def flush(wcur):
        if batch:
            wcur.executemany(UPSERT, batch)
            batch.clear()

    def metric(obs, age, raw_age):
        """A QaL computation from one observed percentile, via continuous calibration lookup.

        Confidence-gated (QaL_spec §11): a *forecast* is shown ONLY for a 'gate-passed' community
        (back-test ~0.90). Lower tiers ('fitted', 'parametric') and observed-only cohorts stay
        calibration-pending; the served record still carries the tier in `coverage`.

        Maturity rule (QaL_spec §6, decide-late): a paper at/beyond the long horizon H is DECIDED —
        its eventual percentile is essentially its observed percentile, with nothing left to
        forecast. For such papers we report QaL = observed with a tight interval (coverage='mature')
        even without a gate-passed calibration, because it is a settled standing, not a forecast."""
        if obs is None:
            return None
        conf = confidence_by_comm.get(sid)
        cell = cl.predict_cell(calib_by_comm.get(sid, {}), age, obs) if sid in calib_by_comm else None
        if cell and conf == "gate-passed":
            return {
                "obs": obs, "calibrated": True, "coverage": "gate-passed",
                "point": round(cell["median"], 1),
                "ci_lo": round(cell["q5"], 1), "ci_hi": round(cell["q95"], 1),
                "class_prob": {f"ge{c}": round(float(cell[f"p_ge{c}"]), 4)
                               for c in (50, 75, 90, 95, 99)},
            }
        if raw_age >= H:  # decided at maturity -> QaL = observed standing, tight interval
            lo, hi = max(0.0, obs - 2.5), min(100.0, obs + 2.5)
            return {"obs": obs, "calibrated": True, "coverage": "mature",
                    "point": round(obs, 1), "ci_lo": round(lo, 1), "ci_hi": round(hi, 1),
                    "class_prob": _class_prob(obs, lo, hi)}
        return {"obs": obs, "calibrated": False, "coverage": conf or "observed",
                "point": None, "ci_lo": None, "ci_hi": None, "class_prob": None}

    def synthetic_metric(parts, age, raw_age, synth_obs):
        """Blend-weighted synthetic-field calibration (mirrors web/lib/synthetic.ts syntheticQal):
        apply EACH constituent subfield's calibration to the focal's percentile IN that subfield,
        blend the posteriors by the synthetic-field weights; confidence (gp_weight) = the share of
        the reference class in back-tested subfields. A forecast shows when >=50% of the weight is
        gate-passed; else the maturity rule for a decided paper; else observed-only."""
        gpW = 0.0
        m = q5 = q95 = 0.0
        acc = {c: 0.0 for c in CUTS}
        for p in (parts or []):
            s, ws, pct = p.get("sid"), p.get("weight", 0.0), p.get("pct")
            if pct is None or confidence_by_comm.get(s) != "gate-passed":
                continue
            cell = cl.predict_cell(calib_by_comm.get(s, {}), age, pct)
            if not cell:
                continue
            gpW += ws
            m += ws * cell["median"]; q5 += ws * cell["q5"]; q95 += ws * cell["q95"]
            for c in CUTS:
                acc[c] += ws * cell[f"p_ge{c}"]
        gp_weight = round(gpW, 2)
        if gpW >= 0.5:
            n = lambda x: x / gpW
            return {"obs": synth_obs, "calibrated": True, "coverage": "gate-passed", "gp_weight": gp_weight,
                    "point": round(n(m), 1), "ci_lo": round(n(q5), 1), "ci_hi": round(n(q95), 1),
                    "class_prob": {f"ge{c}": round(n(acc[c]), 4) for c in CUTS}}
        if raw_age >= H:
            lo, hi = max(0.0, synth_obs - 2.5), min(100.0, synth_obs + 2.5)
            return {"obs": synth_obs, "calibrated": True, "coverage": "mature", "gp_weight": gp_weight,
                    "point": round(synth_obs, 1), "ci_lo": round(lo, 1), "ci_hi": round(hi, 1),
                    "class_prob": _class_prob(synth_obs, lo, hi)}
        return {"obs": synth_obs, "calibrated": False, "coverage": "observed", "gp_weight": gp_weight,
                "point": None, "ci_lo": None, "ci_hi": None, "class_prob": None}

    with conn.cursor() as wcur:
        for (oaid, sid, year, cites, title, doi, p_field, is_oa, is_retr,
             authors, venue, subfield_label, authorships) in rows:
            key = (sid, year)
            has_cohort = key in cohorts
            has_synth = oaid in synth
            if not has_cohort and not has_synth:
                continue  # nothing to say (no field cohort, no synthetic field) -> leave as is
            display = {"title": title, "authors": authors, "venue": venue, "year": year,
                       "cites": cites, "sid": sid, "subfield": subfield_label, "field": p_field,
                       "oa": bool(is_oa), "doi": doi, "retracted": bool(is_retr),
                       "authorships": authorships}
            field_obs = round(obs_percentile(cohorts[key][1], cites or 0), 2) if has_cohort else None
            field_n = cohorts[key][0] if has_cohort else None
            age = max(1, min(H - 1, as_of - year))
            raw_age = as_of - year  # true age (unclamped), for the maturity rule

            # Compute BOTH reference classes (U2): the single-label field cohort and the
            # synthetic field (the official class; §5).
            field_m = metric(field_obs, age, raw_age)
            synth_m = None
            if has_synth:
                n_cit, synth_obs, parts = synth[oaid]
                synth_m = (synthetic_metric(parts, age, raw_age, synth_obs) if parts
                           else metric(synth_obs, age, raw_age))
                synth_m["n"] = n_cit

            # Official = the synthetic field when computed, else the single-label field stand-in.
            official = "synthetic" if has_synth else "field"
            off = synth_m if has_synth else field_m
            # Stored metrics are lean (point + interval + obs); the bulky class_prob is kept
            # only once, in the top-level column, for the official metric (paper-page hero).
            lean = lambda m: None if m is None else {k: m[k] for k in m if k != "class_prob"}
            metrics = {"field": lean(field_m), "synthetic": lean(synth_m), "official": official}

            if has_synth:
                ref = {"field": "synthetic-field", "field_label": "synthetic field",
                       "kind": "synthetic", "vintage_year": year, "n": synth_m["n"],
                       "gp_weight": synth_m.get("gp_weight"), "field_percentile": field_obs}
            else:
                ref = {"field": f"subfields/{sid}", "field_label": labels.get(sid),
                       "kind": "field", "vintage_year": year, "n": field_n}
            ref["coverage"] = off.get("coverage")  # confidence tier of the official metric

            obs = off["obs"]
            calibrated = off["calibrated"]
            if calibrated:
                n_calibrated += 1
            qal_point, ci_lo, ci_hi = off["point"], off["ci_lo"], off["ci_hi"]
            class_prob = off["class_prob"]

            batch.append(
                (oaid, json.dumps(ref), obs, calibrated, qal_point, ci_lo, ci_hi,
                 json.dumps(class_prob) if class_prob else None, json.dumps(metrics),
                 json.dumps(display), model_version, snapshot or "latest")
            )
            n_written += 1
            if len(batch) >= 1000:
                flush(wcur)
        flush(wcur)
    conn.commit()
    conn.close()
    print(f"compute_qal: wrote {n_written} records ({n_calibrated} calibrated, "
          f"{n_written - n_calibrated} calibration-pending)")


if __name__ == "__main__":
    main()
