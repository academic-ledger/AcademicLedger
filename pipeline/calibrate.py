"""Fit Layer-B calibration: (observed pct at age a, community) -> posterior over eventual pct.

The substantive modeling step. Uses MATURE historical cohorts (calibration_years in
cohorts.yml) where both the early signal and the eventual outcome are observed:
  - eventual pct  = within-cohort percentile of cumulative citations at long_horizon_years
  - observed pct  = within-cohort percentile of cumulative citations at age a (a = 1..H-1)
Bin on (community, age, observed-pct decile); store the conditional eventual distribution
(median, 90% interval, mass above each NSF cut) into `calibration_models`.

The raw [5th, 95th] interval is overconfident out-of-sample because the early->eventual
relationship drifts across vintages (the back-test showed ~0.80 coverage). We therefore
apply a per-age split-conformal correction (leave-one-vintage-out) that widens the interval
so held-out coverage is ~0.90, without moving the point estimate (calib_lib.conformal_q).

Condition on the community: citation velocity differs by field (operations resolves faster
than psychology/economics); do NOT pool one mapping across heterogeneous communities (§5).
"""
import os
import calib_lib as cl


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
    model_version = os.environ.get("MODEL_VERSION", "qal-0.1")
    min_bin = int(os.environ.get("CALIB_MIN_BIN", "20"))

    conn = psycopg.connect(db)
    with conn.cursor() as cur:
        for sid in communities:
            # Load matured cohorts with enough support to define within-cohort percentiles.
            prepared = {}
            for yr in cal_years:
                cur.execute(
                    "SELECT counts_by_year FROM works WHERE primary_subfield=%s AND publication_year=%s AND counts_by_year IS NOT NULL",
                    (sid, yr),
                )
                cby = [r[0] for r in cur.fetchall()]
                if len(cby) >= 200:
                    prepared[yr] = cl.prepare(cby, yr, H)
            vintages = list(prepared.keys())
            if len(vintages) < 3:
                print(f"  {sid}: insufficient vintages ({len(vintages)}) — skipped")
                continue

            # Conformal radius per age via leave-one-vintage-out: hold out each vintage in
            # turn, fit on the rest, and pool the conformity scores (honest, uses each
            # vintage as the calibration set exactly once).
            import numpy as np
            pooled_scores = {a: [] for a in range(1, H)}
            for held in vintages:
                fit_v = [v for v in vintages if v != held]
                cells = cl.fit_cells(prepared, fit_v, H, min_bin)
                pa = prepared[held]
                for a in range(1, H):
                    obs_pct, eve_pct = pa[a]
                    for op, y in zip(obs_pct, eve_pct):
                        cell = cells.get((a, min(90, int(op // 10) * 10)))
                        if cell is not None:
                            pooled_scores[a].append(max(cell["q5"] - y, y - cell["q95"]))
            alpha = 0.10
            Q = {}
            for a, sc in pooled_scores.items():
                if sc:
                    sc = np.asarray(sc); n = len(sc)
                    level = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
                    Q[a] = float(np.quantile(sc, level, method="higher"))
                else:
                    Q[a] = 0.0

            # Final cells fit on ALL vintages, widened by the conformal radius.
            cells = cl.fit_cells(prepared, vintages, H, min_bin)
            n_written = 0
            for (age, lo_bin), cell in cells.items():
                lo, hi = cl.predict_interval(cell, Q.get(age, 0.0))
                row = dict(community=sid, age_years=age, obs_pct_bin=lo_bin,
                           eventual_median=cell["median"], ci_lo=lo, ci_hi=hi,
                           n_train=cell["n"], model_version=model_version,
                           p_ge50=cell["p_ge50"], p_ge75=cell["p_ge75"], p_ge90=cell["p_ge90"],
                           p_ge95=cell["p_ge95"], p_ge99=cell["p_ge99"])
                upsert_model(cur, row)
                n_written += 1
            qmean = sum(Q.values()) / max(1, len(Q))
            print(f"  calibrated {sid}: {n_written} cells, mean conformal widen +{qmean:.1f} pts/side")
    conn.commit(); conn.close()


def upsert_model(cur, row):
    cur.execute("""INSERT INTO calibration_models
      (community,age_years,obs_pct_bin,eventual_median,ci_lo,ci_hi,p_ge50,p_ge75,p_ge90,p_ge95,p_ge99,n_train,model_version)
      VALUES (%(community)s,%(age_years)s,%(obs_pct_bin)s,%(eventual_median)s,%(ci_lo)s,%(ci_hi)s,
              %(p_ge50)s,%(p_ge75)s,%(p_ge90)s,%(p_ge95)s,%(p_ge99)s,%(n_train)s,%(model_version)s)
      ON CONFLICT (community,age_years,obs_pct_bin,model_version) DO UPDATE SET
        eventual_median=EXCLUDED.eventual_median, ci_lo=EXCLUDED.ci_lo, ci_hi=EXCLUDED.ci_hi,
        p_ge50=EXCLUDED.p_ge50,p_ge75=EXCLUDED.p_ge75,p_ge90=EXCLUDED.p_ge90,
        p_ge95=EXCLUDED.p_ge95,p_ge99=EXCLUDED.p_ge99,n_train=EXCLUDED.n_train""", row)


if __name__ == "__main__":
    main()
