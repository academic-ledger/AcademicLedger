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

        # Preload calibration cells: {(community, age, obs_bin): row}.
        cur.execute(
            """SELECT community, age_years, obs_pct_bin, eventual_median, ci_lo, ci_hi,
                      p_ge50, p_ge75, p_ge90, p_ge95, p_ge99
                 FROM calibration_models WHERE model_version=%s""",
            (model_version,),
        )
        calib = {}
        for r in cur.fetchall():
            calib[(r[0], r[1], r[2])] = dict(
                median=float(r[3]), ci_lo=float(r[4]), ci_hi=float(r[5]),
                p_ge50=r[6], p_ge75=r[7], p_ge90=r[8], p_ge95=r[9], p_ge99=r[10],
            )

        # Walk every work whose cohort we have a percentile table for.
        cur.execute(
            "SELECT oaid, primary_subfield, publication_year, cited_by_count FROM works "
            "WHERE primary_subfield IS NOT NULL AND publication_year IS NOT NULL"
        )
        rows = cur.fetchall()

    with conn.cursor() as wcur:
        for oaid, sid, year, cites in rows:
            key = (sid, year)
            if key not in cohorts:
                continue  # no percentile table for this cohort -> leave any existing record
            n, cdf = cohorts[key]
            obs = round(obs_percentile(cdf, cites or 0), 2)
            obs_bin = min(90, int(obs // 10) * 10)
            age = max(1, min(H - 1, as_of - year))

            ref = {
                "field": f"subfields/{sid}",
                "field_label": labels.get(sid),
                "vintage_year": year,
                "n": n,
            }

            cell = calib.get((sid, age, obs_bin)) if sid in seed else None
            if cell:
                qal_point = round(cell["median"], 1)
                ci_lo = round(cell["ci_lo"], 1)
                ci_hi = round(cell["ci_hi"], 1)
                class_prob = {
                    "ge50": round(float(cell["p_ge50"]), 4),
                    "ge75": round(float(cell["p_ge75"]), 4),
                    "ge90": round(float(cell["p_ge90"]), 4),
                    "ge95": round(float(cell["p_ge95"]), 4),
                    "ge99": round(float(cell["p_ge99"]), 4),
                }
                calibrated = True
                n_calibrated += 1
            else:
                qal_point = ci_lo = ci_hi = class_prob = None
                calibrated = False

            wcur.execute(
                """INSERT INTO qal_records
                     (oaid, reference_class, obs_percentile, calibrated,
                      qal_point, qal_ci_lo, qal_ci_hi, class_prob, method_version, data_snapshot)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (oaid) DO UPDATE SET
                     reference_class=EXCLUDED.reference_class, obs_percentile=EXCLUDED.obs_percentile,
                     calibrated=EXCLUDED.calibrated, qal_point=EXCLUDED.qal_point,
                     qal_ci_lo=EXCLUDED.qal_ci_lo, qal_ci_hi=EXCLUDED.qal_ci_hi,
                     class_prob=EXCLUDED.class_prob, method_version=EXCLUDED.method_version,
                     data_snapshot=EXCLUDED.data_snapshot, computed_at=now()""",
                (oaid, json.dumps(ref), obs, calibrated, qal_point, ci_lo, ci_hi,
                 json.dumps(class_prob) if class_prob else None, model_version,
                 snapshot or "latest"),
            )
            n_written += 1
    conn.commit()
    conn.close()
    print(f"compute_qal: wrote {n_written} records ({n_calibrated} calibrated, "
          f"{n_written - n_calibrated} calibration-pending)")


if __name__ == "__main__":
    main()
