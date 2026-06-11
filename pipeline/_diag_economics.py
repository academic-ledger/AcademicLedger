"""Diagnose WHERE Economics (2002) loses LOVO coverage — by held-out vintage, by age, and by side
(miss below q5 vs above q95). Offline from the cached cohorts (no OpenAlex). Tells us whether the
under-coverage is a localized/fixable failure (one vintage, one age band, one tail) or diffuse.
Run: python pipeline/_diag_economics.py
"""
import _env
_env.load_env()
import calib_lib as cl
import coverage_rollout as cr

H = cr.H
ALPHA = 0.08
sid = "2002"
cached = cr._load_cohort_cache(sid)
prepared, used = {}, []
for v in cr.MATURE_YEARS:
    rows = cached.get(v, []) if cached else []
    if len(rows) >= 50:
        prepared[v] = cl.prepare([cby for _, cby in rows], v, H)
        used.append(v)

print(f"Economics (2002), alpha={ALPHA}, vintages={used}\n")
print("coverage by HELD-OUT vintage (miss_below = truth under interval, miss_above = over):")
age_tot = {a: [0, 0] for a in range(1, H)}
for held in used:
    fit_v = [v for v in used if v != held]
    cells = cl.fit_cells(prepared, fit_v, H)
    Q = cl.conformal_q_cv(prepared, fit_v, H, alpha=ALPHA)
    hit = tot = below = above = 0
    pa = prepared[held]
    for a in range(1, H):
        op_, ev = pa[a]
        for op, y in zip(op_, ev):
            cell = cl.predict_cell(cells, a, op)
            if cell is None:
                continue
            lo, hi = cl.predict_interval(cell, Q.get(a, 0.0))
            tot += 1
            age_tot[a][1] += 1
            if lo <= y <= hi:
                hit += 1
                age_tot[a][0] += 1
            elif y < lo:
                below += 1
            else:
                above += 1
    print(f"  v{held}: cov={hit/tot:.3f}  below={below/tot:.3f}  above={above/tot:.3f}  (n={tot})")

print("\ncoverage by AGE (pooled over held-out vintages):")
for a in range(1, H):
    h, t = age_tot[a]
    if t:
        print(f"  age {a}: cov={h/t:.3f}  (n={t})")
