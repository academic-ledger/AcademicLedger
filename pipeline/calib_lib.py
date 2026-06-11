"""Shared calibration math, used by both calibrate.py (fit) and backtest.py (validate)
so the production fit and the acceptance test are guaranteed identical.

The model: condition the eventual percentile r_inf on (community, age, observed percentile).
The conditioning on observed percentile is CONTINUOUS, not coarse decile bins — a local
linear quantile fit on a tail-dense grid (QaL_spec.md §5: "binning on (age, r_obs) or by
quantile regression"). Coarse deciles collapsed the whole top decile (90-100) into one cell
whose median ~95, so a paper actually at 99.97 was scored as ~95; the local fit conditions on
~99.97 instead. Because at maturity r_inf ~= r_obs, the local slope -> 1 and the residuals
-> 0, so the posterior converges to identity (point ~= observed, interval ~= 0) as age -> H.

Then a per-age split-conformal correction widens the [q5, q95] interval so held-out coverage
of the 90% interval is ~90% (vintage-drift correction). The point estimate is unchanged.
"""
import bisect

import numpy as np

CUTS = [50, 75, 90, 95, 99]

# Evaluation grid for the conditioning variable (observed percentile), tail-dense so the
# upper tail — where the citation distribution is heaviest and a decile is far too coarse —
# is resolved. The local fit is evaluated at each grid point; predict_cell interpolates.
GRID = [2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5,
        52.5, 57.5, 62.5, 67.5, 72.5, 77.5, 82.5, 87.5, 91.0, 94.0,
        96.5, 98.0, 99.0, 99.5, 99.8, 99.95]

KNN = 400  # window size: the K nearest observed-pct points to a grid point (adaptive width)


def cum_at_age(cby, pub_year, age):
    return sum(v for y, v in (cby or {}).items() if int(y) <= pub_year + age)


def pct_of_all(values):
    """Vectorized within-cohort MID-RANK percentile for every element (QaL_spec.md §5,
    'one convention'): ties — the uncited atom included — take the average rank, so the
    uncited mass sits at 100·p0/2. Same convention for r_obs and r_inf."""
    values = np.asarray(values, dtype=float)
    s = np.sort(values)
    below = np.searchsorted(s, values, side="left")
    upper = np.searchsorted(s, values, side="right")
    midrank = below + (upper - below) / 2.0
    return 100.0 * midrank / len(values)


def prepare(cby_list, vintage, H):
    """For one (community, vintage) cohort -> {age: (obs_pct[], eventual_pct[])}, ages 1..H-1."""
    eventual = np.array([cum_at_age(c, vintage, H) for c in cby_list])
    eve_pct = pct_of_all(eventual)
    per_age = {}
    for a in range(1, H):
        obs = np.array([cum_at_age(c, vintage, a) for c in cby_list])
        per_age[a] = (pct_of_all(obs), eve_pct)
    return per_age


def _local_cell(x, y, g, knn):
    """Local linear fit of eventual (y) on observed (x) using the knn nearest x to grid
    point g; return the conditional posterior of r_inf AT g: median (point), 5th/95th, and
    the mass above each NSF cut. Local-linear (not local-mean) is what makes the maturity
    limit exact identity: when y~=x the slope is ~1 and the prediction at g is ~g."""
    idx = np.argsort(np.abs(x - g))[: min(knn, len(x))]
    xw, yw = x[idx], y[idx]
    if len(xw) >= 8 and np.ptp(xw) > 1e-6:
        b, a = np.polyfit(xw, yw, 1)
        m = a + b * g
        resid = yw - (a + b * xw)
    else:
        m = float(np.median(yw))
        resid = yw - m
    pd = np.clip(m + resid, 0.0, 100.0)  # predicted r_inf distribution at g
    cell = {
        "median": float(np.clip(m, 0.0, 100.0)),
        "q5": float(np.percentile(pd, 5)),
        "q95": float(np.percentile(pd, 95)),
        "n": int(len(xw)),
    }
    for c in CUTS:
        cell[f"p_ge{c}"] = float(np.mean(pd >= c))
    return cell


def fit_cells(prepared, vintages, H, knn=KNN, **_):
    """Pool (obs_pct, eventual_pct) across vintages and fit a local cell at every grid
    point, per age. Keyed (age, grid_point)."""
    cells = {}
    for a in range(1, H):
        xs = np.concatenate([prepared[v][a][0] for v in vintages])
        ys = np.concatenate([prepared[v][a][1] for v in vintages])
        if len(xs) < 10:
            continue
        for g in GRID:
            cells[(a, g)] = _local_cell(xs, ys, g, knn)
    return cells


def predict_cell(cells, age, r_obs):
    """Posterior cell for a focal observed percentile, linearly interpolated between the
    two bracketing grid points (continuous in r_obs)."""
    gs = sorted(g for (a, g) in cells if a == age)
    if not gs:
        return None
    if r_obs <= gs[0]:
        return cells[(age, gs[0])]
    if r_obs >= gs[-1]:
        return cells[(age, gs[-1])]
    i = bisect.bisect_right(gs, r_obs)
    g0, g1 = gs[i - 1], gs[i]
    c0, c1 = cells[(age, g0)], cells[(age, g1)]
    t = (r_obs - g0) / (g1 - g0)
    out = {k: c0[k] * (1 - t) + c1[k] * t for k in ("median", "q5", "q95",
           "p_ge50", "p_ge75", "p_ge90", "p_ge95", "p_ge99")}
    out["n"] = min(c0["n"], c1["n"])
    return out


def conformal_q(prepared, fit_vintages, cal_vintages, H, alpha=0.10, knn=KNN):
    """Per-age conformal radius Q_a from a fit/cal split, using the continuous predict_cell
    interval. Score E = max(q5 - y, y - q95); Q_a = the (1-alpha) quantile of E."""
    cells = fit_cells(prepared, fit_vintages, H, knn)
    scores = {a: [] for a in range(1, H)}
    for v in cal_vintages:
        pa = prepared[v]
        for a in range(1, H):
            obs_pct, eve_pct = pa[a]
            for op, y in zip(obs_pct, eve_pct):
                cell = predict_cell(cells, a, op)
                if cell is None:
                    continue
                scores[a].append(max(cell["q5"] - y, y - cell["q95"]))
    Q = {}
    for a, sc in scores.items():
        if not sc:
            Q[a] = 0.0
            continue
        sc = np.asarray(sc)
        n = len(sc)
        level = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
        Q[a] = float(np.quantile(sc, level, method="higher"))
    return Q


def conformal_q_cv(prepared, vintages, H, alpha=0.10, knn=KNN):
    """Cross-vintage conformal radius. A single fit/cal split estimates the radius from ONE
    held-out vintage, which underestimates the spread the model faces when it predicts a *new*
    vintage from past ones (eventual-percentile residuals shift across vintages). Instead, hold
    each training vintage out in turn, score it against a model fit on the rest, pool those
    leave-one-vintage-out residuals, and take the (1-alpha) quantile per age. This is the residual
    distribution the deployment actually sees, so the widened interval attains ~(1-alpha) coverage
    on a genuinely held-out vintage rather than under-covering it. Needs >=2 vintages; falls back
    to the single-split conformal_q for one."""
    if len(vintages) < 2:
        return conformal_q(prepared, vintages, vintages, H, alpha, knn)
    scores = {a: [] for a in range(1, H)}
    for held in vintages:
        fit_v = [v for v in vintages if v != held]
        cells = fit_cells(prepared, fit_v, H, knn)
        pa = prepared[held]
        for a in range(1, H):
            obs_pct, eve_pct = pa[a]
            for op, y in zip(obs_pct, eve_pct):
                cell = predict_cell(cells, a, op)
                if cell is None:
                    continue
                scores[a].append(max(cell["q5"] - y, y - cell["q95"]))
    Q = {}
    for a, sc in scores.items():
        if not sc:
            Q[a] = 0.0
            continue
        sc = np.asarray(sc)
        n = len(sc)
        level = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
        Q[a] = float(np.quantile(sc, level, method="higher"))
    return Q


def predict_interval(cell, Q_a):
    """Conformally widened 90% interval, clipped to [0, 100]."""
    lo = max(0.0, cell["q5"] - Q_a)
    hi = min(100.0, cell["q95"] + Q_a)
    return lo, hi
