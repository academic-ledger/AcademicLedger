"""Calibration back-test — the Level-0 acceptance gate (QaL_spec.md §10.1).

Does the (conformalized) 90% posterior interval actually cover the realized eventual
percentile ~90% of the time, across ages and communities? Honest leave-one-vintage-out:
the held-out test vintage is used for NOTHING in fitting — neither the bins nor the
conformal radius (which is computed by an inner leave-one-vintage-out over the training
vintages only). This back-tests the exact methodology calibrate.py ships.

Pass condition: overall coverage within [0.88, 0.93] (target 0.90), with adequate support.

Usage:  DATABASE_URL=... python pipeline/backtest.py
"""
import os
import numpy as np
import calib_lib as cl


def conformal_from_train(prepared, train_vintages, H, min_bin):
    """Per-age conformal radius from train vintages only (inner leave-one-vintage-out)."""
    pooled = {a: [] for a in range(1, H)}
    for held in train_vintages:
        fit_v = [v for v in train_vintages if v != held]
        cells = cl.fit_cells(prepared, fit_v, H)
        pa = prepared[held]
        for a in range(1, H):
            obs_pct, eve_pct = pa[a]
            for op, y in zip(obs_pct, eve_pct):
                cell = cl.predict_cell(cells, a, op)
                if cell is not None:
                    pooled[a].append(max(cell["q5"] - y, y - cell["q95"]))
    Q = {}
    for a, sc in pooled.items():
        if sc:
            sc = np.asarray(sc); n = len(sc)
            level = min(1.0, np.ceil((n + 1) * 0.90) / n)
            Q[a] = float(np.quantile(sc, level, method="higher"))
        else:
            Q[a] = 0.0
    return Q


def main():
    db = os.environ.get("DATABASE_URL")
    if not db:
        print("No DATABASE_URL; this job expects the datastore. See README.")
        return
    import psycopg, yaml

    cfg = yaml.safe_load(open("pipeline/cohorts.yml"))
    H = cfg["long_horizon_years"]
    cal_years = cfg["calibration_years"]
    communities = list(cfg["seed_subfields"])
    min_bin = int(os.environ.get("BACKTEST_MIN_BIN", "20"))

    conn = psycopg.connect(db)
    prepared_by_comm = {}
    with conn.cursor() as cur:
        for sid in communities:
            prepared = {}
            for yr in cal_years:
                cur.execute(
                    "SELECT counts_by_year FROM works WHERE primary_subfield=%s AND publication_year=%s AND counts_by_year IS NOT NULL",
                    (sid, yr),
                )
                cby = [r[0] for r in cur.fetchall()]
                if len(cby) >= 200:
                    prepared[yr] = cl.prepare(cby, yr, H)
            if len(prepared) >= 3:
                prepared_by_comm[sid] = prepared
    conn.close()

    overall = [0, 0]
    by_age = {a: [0, 0] for a in range(1, H)}
    per_comm = {}

    for sid, prepared in prepared_by_comm.items():
        vintages = list(prepared.keys())
        c = [0, 0]
        for test_v in vintages:
            train = [v for v in vintages if v != test_v]
            Q = conformal_from_train(prepared, train, H, min_bin)   # train-only radius
            cells = cl.fit_cells(prepared, train, H)                # train-only fit
            pa = prepared[test_v]
            for a in range(1, H):
                obs_pct, eve_pct = pa[a]
                for op, y in zip(obs_pct, eve_pct):
                    cell = cl.predict_cell(cells, a, op)
                    if cell is None:
                        continue
                    lo, hi = cl.predict_interval(cell, Q.get(a, 0.0))
                    hit = 1 if (lo <= y <= hi) else 0
                    overall[0] += hit; overall[1] += 1
                    c[0] += hit; c[1] += 1
                    by_age[a][0] += hit; by_age[a][1] += 1
        per_comm[sid] = c

    print("=== Calibration back-test (conformalized, leave-one-vintage-out, 90% interval) ===")
    print(f"horizon H={H}, calibration vintages={cal_years}\n")
    print("By community:")
    for sid, (h, n) in per_comm.items():
        print(f"  {sid}: coverage {h / n:.3f}  (n={n})" if n else f"  {sid}: no test points")
    print("\nBy age (years since publication):")
    for a in range(1, H):
        h, n = by_age[a]
        if n:
            print(f"  age {a}: coverage {h / n:.3f}  (n={n})")
    if overall[1] == 0:
        print("\nNo test points — are the calibration cohorts pulled (counts_by_year present)?")
        return
    cov = overall[0] / overall[1]
    print(f"\nOVERALL coverage: {cov:.3f}  (target 0.90, n={overall[1]})")
    passed = 0.88 <= cov <= 0.93
    print("GATE:", "PASS ✓" if passed else "FAIL ✗ — calibration not yet defensible")
    return passed


if __name__ == "__main__":
    main()
