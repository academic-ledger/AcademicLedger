"""Fit Layer-B calibration: (observed pct at age a, community) -> posterior over eventual pct.

The substantive modeling step. Uses MATURE historical cohorts (calibration_years in
cohorts.yml) where both the early signal and the eventual outcome are observed:
  - eventual pct  = within-cohort percentile of cumulative citations at long_horizon_years
  - observed pct  = within-cohort percentile of cumulative citations at age a (a = 1..H)
Bin on (community, age, observed-pct) and store the conditional distribution of eventual
pct (median, 5th/95th, and mass above each NSF cut point) into `calibration_models`.

This generalizes the early-signal study (docs/early_signal_result.md) from one cohort to
the seed communities and multiple vintages. Conditioning on the community matters because
citation velocity differs by field (operations resolves faster than psychology/economics);
do NOT pool a single mapping across heterogeneous communities (QaL_spec.md §5).
"""
import os, json
import numpy as np

CUTS = [50, 75, 90, 95, 99]

def cum_at_age(counts_by_year, pub_year, age):
    """Cumulative citations from publication through `age` years."""
    return sum(v for y, v in counts_by_year.items() if int(y) <= pub_year + age)

def percentile_of(values, x):
    values = np.sort(np.asarray(values))
    return 100 * np.searchsorted(values, x, side="right") / len(values)

def main():
    db = os.environ.get("DATABASE_URL")
    if not db:
        print("No DATABASE_URL; this job expects the datastore. See README."); return
    import psycopg, yaml
    cfg = yaml.safe_load(open("pipeline/cohorts.yml"))
    H = cfg["long_horizon_years"]
    cal_years = cfg["calibration_years"]
    communities = list(cfg["seed_subfields"])
    conn = psycopg.connect(db)
    model_version = os.environ.get("MODEL_VERSION", "qal-0.1")
    with conn.cursor() as cur:
        for sid in communities:
            for yr in cal_years:
                cur.execute("""SELECT counts_by_year FROM works
                               WHERE primary_subfield=%s AND publication_year=%s""", (sid, yr))
                cbys = [r[0] for r in cur.fetchall()]
                if len(cbys) < 200:   # need support
                    continue
                eventual = [cum_at_age(c, yr, H) for c in cbys]
                for age in range(1, H):
                    obs = [cum_at_age(c, yr, age) for c in cbys]
                    obs_pct = [percentile_of(obs, x) for x in obs]
                    eve_pct = [percentile_of(eventual, x) for x in eventual]
                    # bin observed pct into deciles, store conditional eventual distribution
                    for lo in range(0, 100, 10):
                        idx = [i for i, p in enumerate(obs_pct) if lo <= p < lo + 10]
                        if len(idx) < 20:
                            continue
                        ev = np.array([eve_pct[i] for i in idx])
                        row = dict(community=sid, age_years=age, obs_pct_bin=lo,
                                   eventual_median=float(np.median(ev)),
                                   ci_lo=float(np.percentile(ev, 5)), ci_hi=float(np.percentile(ev, 95)),
                                   n_train=len(idx), model_version=model_version)
                        for c in CUTS:
                            row[f"p_ge{c}"] = float(np.mean(ev >= c))
                        upsert_model(cur, row)
            print(f"  calibrated {sid}")
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
