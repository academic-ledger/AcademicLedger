"""Offline conformal-alpha sweep for the near-miss subfields + spot-checks.

Pulls each subfield's matured cohorts ONCE (deterministic seed=42) into data/calib_cache/, then
sweeps the conformal target alpha and reports nested-LOVO back-test coverage at each — no DB writes,
no re-pull on re-run (cached). Goal: the smallest widening (largest alpha) that lands the three
near-misses >= 0.88 while keeping the gate-passed spot-check and the seed <= 0.97.
Run: python pipeline/_tune_alpha.py
"""
import _env
_env.load_env()
import calib_lib as cl
import coverage_rollout as cr

H = cr.H
SUBS = [
    ("3312", "Sociology (near-miss)"),
    ("2002", "Economics (near-miss)"),
    ("1407", "Org Behavior (near-miss)"),
    ("1404", "MIS (gate-passed)"),
    ("1803", "seed MS&OR"),
]
ALPHAS = [0.10, 0.09, 0.08, 0.07, 0.06]


def get_prepared(sid):
    cached = cr._load_cohort_cache(sid)
    if cached is None:
        cached = {}
        for v in cr.MATURE_YEARS:
            cached[v] = cr._pull_cohort_mem(sid, v, cr.CALIB_N)
        cr._save_cohort_cache(sid, cached)
        print(f"  [{sid}] pulled + cached", flush=True)
    else:
        print(f"  [{sid}] loaded from cache", flush=True)
    prepared, used = {}, []
    for v in cr.MATURE_YEARS:
        rows = cached.get(v, [])
        if len(rows) >= 50:
            prepared[v] = cl.prepare([cby for _, cby in rows], v, H)
            used.append(v)
    return prepared, used


print("pulling/loading cohorts (one-time):", flush=True)
prep = {sid: get_prepared(sid) for sid, _ in SUBS}
print("\ncoverage by conformal alpha (gate band [0.88, 0.97]):", flush=True)
print(f"{'sid':6}{'name':24}" + "".join(f"a={a:<5}" for a in ALPHAS), flush=True)
for sid, name in SUBS:
    prepared, used = prep[sid]
    cells = ""
    for a in ALPHAS:
        c = cr._backtest_coverage(prepared, used, alpha=a)
        cells += (f"{c:.3f} " if c is not None else "  -   ")
    print(f"{sid:6}{name:24}{cells}", flush=True)
print("\npick the LARGEST alpha (least widening) with near-misses >=0.88 and spot-checks <=0.97", flush=True)
