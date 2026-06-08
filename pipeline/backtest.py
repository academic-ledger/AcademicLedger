"""Calibration back-test — the Level-0 acceptance gate (QaL_spec.md §10.1).

Does the 90% posterior interval actually cover the realized eventual percentile ~90%
of the time, across ages and communities? We answer it honestly with
leave-one-vintage-out cross-validation, re-fitting the early->eventual mapping on the
TRAINING vintages and scoring coverage on the held-out vintage (so we never test on
data we trained on). This is independent of calibration_models in the DB: it back-tests
the *methodology*, not a stored fit.

Pass condition: overall coverage within [0.85, 0.95] (target 0.90), with adequate support.

Usage:  DATABASE_URL=... python pipeline/backtest.py
"""
import os
import numpy as np


def cum_at_age(cby, pub_year, age):
    return sum(v for y, v in cby.items() if int(y) <= pub_year + age)


def pct_of(values, x):
    values = np.sort(np.asarray(values, dtype=float))
    return 100.0 * np.searchsorted(values, x, side="right") / len(values)


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
    min_train = int(os.environ.get("BACKTEST_MIN_BIN", "20"))

    conn = psycopg.connect(db)

    # Load matured calibration cohorts: community -> {vintage: [counts_by_year, ...]}
    cohorts = {}
    with conn.cursor() as cur:
        for sid in communities:
            cohorts[sid] = {}
            for yr in cal_years:
                cur.execute(
                    "SELECT counts_by_year FROM works WHERE primary_subfield=%s AND publication_year=%s",
                    (sid, yr),
                )
                cby = [r[0] for r in cur.fetchall()]
                if len(cby) >= 200:  # need support to define percentiles
                    cohorts[sid][yr] = cby
    conn.close()

    # Precompute, per (community, vintage), the obs_pct@age and eventual_pct arrays.
    def cohort_arrays(cby_list, vintage):
        eventual = np.array([cum_at_age(c, vintage, H) for c in cby_list])
        eve_pct = np.array([pct_of(eventual, x) for x in eventual])
        per_age = {}
        for a in range(1, H):
            obs = np.array([cum_at_age(c, vintage, a) for c in cby_list])
            per_age[a] = (np.array([pct_of(obs, x) for x in obs]), eve_pct)
        return per_age

    prepared = {
        sid: {v: cohort_arrays(cby, v) for v, cby in vmap.items()}
        for sid, vmap in cohorts.items()
    }

    # Leave-one-vintage-out.
    overall_hits, overall_n = 0, 0
    by_age = {a: [0, 0] for a in range(1, H)}
    per_community = {}

    for sid, vmap in prepared.items():
        vintages = list(vmap.keys())
        if len(vintages) < 2:
            continue
        c_hits, c_n = 0, 0
        for held in vintages:
            # Build training bins: (age, obs_bin) -> list of eventual_pct from OTHER vintages.
            bins = {}
            for v in vintages:
                if v == held:
                    continue
                for a in range(1, H):
                    obs_pct, eve_pct = vmap[v][a]
                    for op, ep in zip(obs_pct, eve_pct):
                        b = (a, min(90, int(op // 10) * 10))
                        bins.setdefault(b, []).append(ep)
            # Score the held-out vintage.
            for a in range(1, H):
                obs_pct, eve_pct = vmap[held][a]
                for op, realized in zip(obs_pct, eve_pct):
                    b = (a, min(90, int(op // 10) * 10))
                    train = bins.get(b)
                    if not train or len(train) < min_train:
                        continue
                    lo = np.percentile(train, 5)
                    hi = np.percentile(train, 95)
                    hit = 1 if (lo <= realized <= hi) else 0
                    overall_hits += hit; overall_n += 1
                    c_hits += hit; c_n += 1
                    by_age[a][0] += hit; by_age[a][1] += 1
        per_community[sid] = (c_hits, c_n)

    # Report.
    print("=== Calibration back-test (leave-one-vintage-out, 90% interval) ===")
    print(f"horizon H={H}, calibration vintages={cal_years}\n")
    print("By community:")
    for sid, (h, n) in per_community.items():
        cov = h / n if n else float("nan")
        print(f"  {sid}: coverage {cov:.3f}  (n={n})")
    print("\nBy age (years since publication):")
    for a in range(1, H):
        h, n = by_age[a]
        if n:
            print(f"  age {a}: coverage {h / n:.3f}  (n={n})")
    if overall_n == 0:
        print("\nNo test points — are the calibration cohorts pulled (counts_by_year present)?")
        return
    overall = overall_hits / overall_n
    print(f"\nOVERALL coverage: {overall:.3f}  (target 0.90, n={overall_n})")
    passed = 0.85 <= overall <= 0.95
    print("GATE:", "PASS ✓" if passed else "FAIL ✗ — calibration not yet defensible")
    return passed


if __name__ == "__main__":
    main()
