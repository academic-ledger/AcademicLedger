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

import calib_lib as cl

CUTS = [50, 75, 90, 95, 99]


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

    conn = psycopg.connect(db)
    n_written = 0
    n_calibrated = 0
    with conn.cursor() as cur:
        # Preload cohort percentile tables into memory: {(subfield, year): (n, cdf)}.
        if snapshot:
            cur.execute(
                "SELECT subfield, publication_year, n, cdf FROM cohort_percentiles WHERE snapshot=%s",
                (snapshot,),
            )
        else:
            # latest snapshot per (subfield, year) by lexical max (snapshots are date-stamped)
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
                      p_ge50, p_ge75, p_ge90, p_ge95, p_ge99
                 FROM calibration_models WHERE model_version=%s""",
            (model_version,),
        )
        calib_by_comm = {}
        for r in cur.fetchall():
            calib_by_comm.setdefault(r[0], {})[(r[1], float(r[2]))] = dict(
                median=float(r[3]), q5=float(r[4]), q95=float(r[5]), n=1,
                p_ge50=float(r[6]), p_ge75=float(r[7]), p_ge90=float(r[8]),
                p_ge95=float(r[9]), p_ge99=float(r[10]),
            )

        # Preload the cached synthetic field — the OFFICIAL reference class where available
        # (QaL_spec.md §5). {oaid: (n_citers, synthetic_percentile)}.
        cur.execute("SELECT oaid, n_citers, obs_percentile FROM synthetic_field")
        synth = {r[0]: (r[1], float(r[2])) for r in cur.fetchall()}

        # Walk every work whose cohort we have a percentile table for. Pull the display fields
        # too so qal_records is self-sufficient for serving (the cache; works is just staging).
        cur.execute(
            "SELECT oaid, primary_subfield, publication_year, cited_by_count, title, doi, "
            "       primary_field, is_oa, is_retracted, raw->>'authors', raw->>'venue', "
            "       raw->>'subfield_label' "
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

    def metric(obs, age):
        """A QaL computation from one observed percentile, via continuous calibration lookup."""
        if obs is None:
            return None
        cell = cl.predict_cell(calib_by_comm.get(sid, {}), age, obs) if sid in seed else None
        if cell:
            return {
                "obs": obs, "calibrated": True,
                "point": round(cell["median"], 1),
                "ci_lo": round(cell["q5"], 1), "ci_hi": round(cell["q95"], 1),
                "class_prob": {f"ge{c}": round(float(cell[f"p_ge{c}"]), 4)
                               for c in (50, 75, 90, 95, 99)},
            }
        return {"obs": obs, "calibrated": False, "point": None,
                "ci_lo": None, "ci_hi": None, "class_prob": None}

    with conn.cursor() as wcur:
        for (oaid, sid, year, cites, title, doi, p_field, is_oa, is_retr,
             authors, venue, subfield_label) in rows:
            key = (sid, year)
            has_cohort = key in cohorts
            has_synth = oaid in synth
            if not has_cohort and not has_synth:
                continue  # nothing to say (no field cohort, no synthetic field) -> leave as is
            display = {"title": title, "authors": authors, "venue": venue, "year": year,
                       "cites": cites, "sid": sid, "subfield": subfield_label, "field": p_field,
                       "oa": bool(is_oa), "doi": doi, "retracted": bool(is_retr)}
            field_obs = round(obs_percentile(cohorts[key][1], cites or 0), 2) if has_cohort else None
            field_n = cohorts[key][0] if has_cohort else None
            age = max(1, min(H - 1, as_of - year))

            # Compute BOTH reference classes (U2): the single-label field cohort and the
            # synthetic field (the official class; §5).
            field_m = metric(field_obs, age)
            synth_m = None
            if has_synth:
                n_cit, synth_obs = synth[oaid]
                synth_m = metric(synth_obs, age)
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
                       "field_percentile": field_obs}
            else:
                ref = {"field": f"subfields/{sid}", "field_label": labels.get(sid),
                       "kind": "field", "vintage_year": year, "n": field_n}

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
