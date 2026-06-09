"""Regression tests for the Layer-B calibration resolution + maturity convergence (§5).

A prior build binned the conditioning variable (observed percentile) into coarse deciles, so
the whole top decile (90-100) collapsed into one cell whose median ~95 — a 15-year-old paper
at the 99.97th percentile was scored QaL ~95 with a 10-point interval. The continuous
local-linear fit conditions on ~99.97 and, because at maturity r_inf ~= r_obs, converges to
identity (point ~= observed, interval ~= 0).

Run:  DATABASE_URL=... python pipeline/test_calibration.py   (DB only; no OpenAlex)
"""
import os
import sys

import psycopg
import yaml

import calib_lib as cl


def _fit(sid="1800"):
    cfg = yaml.safe_load(open("cohorts.yml"))
    H, cal = cfg["long_horizon_years"], cfg["calibration_years"]
    with psycopg.connect(os.environ["DATABASE_URL"]) as c, c.cursor() as cur:
        prepared = {}
        for yr in cal:
            cur.execute(
                "select counts_by_year from works where primary_subfield=%s and publication_year=%s "
                "and counts_by_year is not null", (sid, yr))
            cby = [r[0] for r in cur.fetchall()]
            if len(cby) >= 200:
                prepared[yr] = cl.prepare(cby, yr, H)
    return cl.fit_cells(prepared, list(prepared.keys()), H), H


def test_maturity_converges_to_identity():
    """At the most mature calibration age, the point tracks observed across the whole range
    (not collapsed to a decile median) and the interval is narrow."""
    cells, H = _fit("1800")
    age = H - 1
    for obs in [20, 40, 60, 80, 90, 99, 99.97]:
        cell = cl.predict_cell(cells, age, obs)
        width = cell["q95"] - cell["q5"]
        assert abs(cell["median"] - obs) <= 6, f"obs {obs}: point {cell['median']:.1f} not tracking observed"
        assert width <= 14, f"obs {obs}: mature interval too wide ({width:.1f})"
    print("  ok: at maturity point tracks observed (identity) with a narrow interval, across the range")


def test_top_percentile_is_not_decile_median():
    """The exact regression: a mature paper at 99.97 must score ~99-100 (NOT ~95), with the
    bucket mass in 99-100 — i.e. the within-decile position is used."""
    cells, H = _fit("1800")
    cell = cl.predict_cell(cells, H - 1, 99.97)
    assert cell["median"] >= 99.0, f"99.97 mature should be ~99-100, got {cell['median']:.1f}"
    assert (cell["q95"] - cell["q5"]) <= 6, f"interval should be narrow, got {cell['q95']-cell['q5']:.1f}"
    assert cell["p_ge99"] >= 0.7, f"bucket mass should sit in 99-100, p_ge99={cell['p_ge99']:.2f}"
    print(f"  ok: 99.97 @ maturity -> {cell['median']:.1f} [{cell['q5']:.1f},{cell['q95']:.1f}] p_ge99={cell['p_ge99']:.2f}")


def test_young_paper_keeps_wide_interval():
    """Decide-late must survive the fix: a young top paper still carries real uncertainty."""
    cells, H = _fit("1800")
    cell = cl.predict_cell(cells, 2, 99.97)
    assert (cell["q95"] - cell["q5"]) >= 3, "a 2-year-old top paper should still be uncertain"
    print(f"  ok: young (age 2) 99.97 -> [{cell['q5']:.1f},{cell['q95']:.1f}] (still wide)")


def test_served_W2161498332():
    """The reported case, end to end: False-Positive Psychology (1800/2011, obs 99.97, ~15y)
    must serve QaL ~99-100 with a narrow interval and bucket mass in 99-100."""
    with psycopg.connect(os.environ["DATABASE_URL"]) as c, c.cursor() as cur:
        cur.execute("select obs_percentile, qal_point, qal_ci_lo, qal_ci_hi, class_prob "
                    "from qal_records where oaid='W2161498332'")
        r = cur.fetchone()
    assert r, "W2161498332 not served"
    obs, pt, lo, hi, cp = float(r[0]), float(r[1]), float(r[2]), float(r[3]), r[4]
    assert pt >= 98.5, f"point should be ~99-100, got {pt}"
    assert (hi - lo) <= 8, f"interval should be narrow, got [{lo},{hi}]"
    assert cp["ge99"] >= 0.6, f"bucket mass should sit in 99-100, ge99={cp['ge99']}"
    print(f"  ok: W2161498332 served {pt} [{lo},{hi}] ge99={cp['ge99']} (obs {obs})")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))  # so cohorts.yml resolves
    tests = [test_maturity_converges_to_identity, test_top_percentile_is_not_decile_median,
             test_young_paper_keeps_wide_interval, test_served_W2161498332]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"  FAIL {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
