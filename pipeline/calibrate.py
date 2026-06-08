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
    min_bin = int(os.environ.get("CALIB_MIN_BIN", "20"))
    with conn.cursor() as cur:
        for sid in communities:
            # Pool eventual-percentile samples across ALL calibration vintages before fitting,
            # keyed by (age, observed-pct decile). Pooling (not per-vintage overwrite) is what
            # gives each cell enough support and matches the back-test procedure.
            bins = {}  # (age, obs_bin) -> [eventual_pct, ...]
            for yr in cal_years:
                cur.execute("""SELECT counts_by_year FROM works
                               WHERE primary_subfield=%s AND publication_year=%s""", (sid, yr))
                cbys = [r[0] for r in cur.fetchall()]
                if len(cbys) < 200:   # need support to define within-cohort percentiles
                    continue
                eventual = [cum_at_age(c, yr, H) for c in cbys]
                eve_pct = [percentile_of(eventual, x) for x in eventual]
                for age in range(1, H):
                    obs = [cum_at_age(c, yr, age) for c in cbys]
                    obs_pct = [percentile_of(obs, x) for x in obs]
                    for op, ep in zip(obs_pct, eve_pct):
                        bins.setdefault((age, min(90, int(op // 10) * 10)), []).append(ep)
            n_cells = 0
            for (age, lo), ev_list in bins.items():
                if len(ev_list) < min_bin:
                    continue
                ev = np.asarray(ev_list)
                row = dict(community=sid, age_years=age, obs_pct_bin=lo,
                           eventual_median=float(np.median(ev)),
                           ci_lo=float(np.percentile(ev, 5)), ci_hi=float(np.percentile(ev, 95)),
                           n_train=len(ev), model_version=model_version)
                for c in CUTS:
                    row[f"p_ge{c}"] = float(np.mean(ev >= c))
                upsert_model(cur, row)
                n_cells += 1
            print(f"  calibrated {sid}: {n_cells} cells")
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
