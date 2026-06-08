"""Build per-(subfield, year) citation->percentile tables (the universal layer).

Reads `works`, writes `cohort_percentiles`. Percentile is the empirical CDF of
cited_by_count within the cohort; the uncited mass gets one shared rank.
Makes a paper's observed percentile an O(1) interpolated lookup at read time.
"""
import os, json
import numpy as np

def cdf_breakpoints(cites):
    # MID-RANK percentile per distinct citation count (QaL_spec.md §5 denominator rule):
    # ties take the average rank, so the uncited atom (cites=0) lands at 100·p0/2 rather
    # than at the top of its block. p0 (the zero-citation share) is recoverable as the
    # bottom breakpoint: pct(0) = 100·p0/2.
    cites = np.sort(np.asarray(cites))
    n = len(cites)
    vals = np.unique(cites)
    out = []
    for v in vals:
        below = int(np.searchsorted(cites, v, side="left"))
        equal = int(np.searchsorted(cites, v, side="right")) - below
        midrank_pct = 100.0 * (below + equal / 2.0) / n
        out.append({"cites": int(v), "pct": float(round(midrank_pct, 3))})
    return n, out

def main():
    db = os.environ.get("DATABASE_URL")
    snapshot = os.environ.get("OPENALEX_SNAPSHOT", "openalex-dev")
    # A within-cohort percentile is only meaningful with enough support; skip thin cohorts
    # (this also protects any small demo-seeded cohorts from producing junk percentiles).
    min_n = int(os.environ.get("MIN_COHORT_N", "50"))
    if not db:
        print("No DATABASE_URL; this job expects the datastore. See README."); return
    import psycopg
    conn = psycopg.connect(db)
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT primary_subfield, publication_year FROM works WHERE primary_subfield IS NOT NULL")
        pairs = cur.fetchall()
        for sid, yr in pairs:
            cur.execute("SELECT cited_by_count FROM works WHERE primary_subfield=%s AND publication_year=%s", (sid, yr))
            cites = [r[0] for r in cur.fetchall()]
            if len(cites) < min_n:
                continue
            n, cdf = cdf_breakpoints(cites)
            cur.execute("""INSERT INTO cohort_percentiles (subfield,publication_year,n,cdf,snapshot)
                           VALUES (%s,%s,%s,%s,%s)
                           ON CONFLICT (subfield,publication_year,snapshot)
                           DO UPDATE SET n=EXCLUDED.n, cdf=EXCLUDED.cdf""",
                        (sid, yr, n, json.dumps(cdf), snapshot))
            print(f"  {sid} {yr}: n={n}, {len(cdf)} breakpoints")
    conn.commit(); conn.close()

if __name__ == "__main__":
    main()
