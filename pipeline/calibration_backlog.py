"""Calibration backlog — subfields ranked by IMPACT to the OID department.

Impact = total synthetic-field weight the subfield holds across all computed papers (synthetic_field
.parts). Calibrating a high-impact subfield flips the most papers from "pending" to a forecast,
because the blend-weighted QaL shows a forecast once >=50% of a paper's reference-class weight sits
in back-tested (gate-passed) subfields. Each subfield is tagged with its current state:
  gate-passed  -> done (back-tested)
  fitted       -> calibrated but below the 0.88 gate (re-sample may push it over)
  uncalibrated -> has a percentile cohort but no calibration model
  no-cohort    -> not sampled at all (needs skeleton + sample + calibrate)

Writes data/calibration_backlog.json and prints the priority order (non-gate-passed, by impact).

Usage: DATABASE_URL=... python pipeline/calibration_backlog.py
"""
import os
import json


def main():
    db = os.environ.get("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL not set")
    import psycopg
    with psycopg.connect(db, connect_timeout=15) as c, c.cursor() as cur:
        cur.execute("SELECT id, name FROM subfields")
        names = dict(cur.fetchall())
        cur.execute("SELECT DISTINCT community, confidence FROM calibration_models")
        tier = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute("SELECT DISTINCT subfield FROM cohort_percentiles")
        have_cohort = {r[0] for r in cur.fetchall()}
        cur.execute(
            """SELECT sid, SUM(weight) tw, COUNT(*) n FROM (
                 SELECT (jsonb_array_elements(parts)->>'sid') sid,
                        (jsonb_array_elements(parts)->>'weight')::float weight
                 FROM synthetic_field WHERE parts IS NOT NULL) t
               GROUP BY sid ORDER BY tw DESC"""
        )
        rows = cur.fetchall()

    total = sum(r[1] for r in rows) or 1.0
    backlog = []
    for sid, tw, n in rows:
        state = tier.get(sid) or ("uncalibrated" if sid in have_cohort else "no-cohort")
        backlog.append({
            "sid": sid, "name": names.get(sid, sid),
            "impact_pct": round(100 * tw / total, 2), "n_papers": n, "state": state,
        })

    os.makedirs("data", exist_ok=True)
    with open("data/calibration_backlog.json", "w") as f:
        json.dump({"ranked": backlog, "total_weight": round(total, 2)}, f, indent=2)

    priority = [b for b in backlog if b["state"] != "gate-passed"]
    print(f"wrote data/calibration_backlog.json ({len(backlog)} subfields)\n")
    print("CALIBRATION PRIORITY (non-gate-passed, by impact):")
    print(f"  {'sid':6} {'impact':>7} {'state':13} subfield")
    cum_gp = sum(b["impact_pct"] for b in backlog if b["state"] == "gate-passed")
    print(f"  -- gate-passed already covers {cum_gp:.0f}% of department weight --")
    for b in priority[:15]:
        print(f"  {b['sid']:6} {b['impact_pct']:6.1f}% {b['state']:13} {b['name']}")


if __name__ == "__main__":
    main()
