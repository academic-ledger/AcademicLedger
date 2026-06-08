"""Shared calibration math, used by both calibrate.py (fit) and backtest.py (validate)
so the production fit and the acceptance test are guaranteed identical.

The model: condition the eventual percentile r_inf on (community, age, observed-pct decile),
read its empirical [median, 5th, 95th] and the mass above each NSF cut. Then apply a
split-conformal correction per age: widen the [q5, q95] interval by Q_a so that held-out
coverage of the 90% interval is ~90%, correcting the in-sample overconfidence that comes
from vintage-to-vintage drift. The point estimate (median) is unchanged.
"""
import numpy as np

CUTS = [50, 75, 90, 95, 99]


def cum_at_age(cby, pub_year, age):
    return sum(v for y, v in (cby or {}).items() if int(y) <= pub_year + age)


def pct_of_all(values):
    """Vectorized within-cohort percentile (share at-or-below) for every element."""
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind="mergesort")
    s = values[order]
    ranks = np.searchsorted(s, values, side="right")
    return 100.0 * ranks / len(values)


def prepare(cby_list, vintage, H):
    """For one (community, vintage) cohort -> {age: (obs_pct[], eventual_pct[])}, ages 1..H-1."""
    eventual = np.array([cum_at_age(c, vintage, H) for c in cby_list])
    eve_pct = pct_of_all(eventual)
    per_age = {}
    for a in range(1, H):
        obs = np.array([cum_at_age(c, vintage, a) for c in cby_list])
        per_age[a] = (pct_of_all(obs), eve_pct)
    return per_age


def _bin(op):
    return min(90, int(op // 10) * 10)


def fit_cells(prepared, vintages, H, min_bin=20):
    """Pool eventual-pct samples across `vintages` -> cells keyed (age, obs_bin)."""
    pool = {}
    for v in vintages:
        pa = prepared[v]
        for a in range(1, H):
            obs_pct, eve_pct = pa[a]
            for op, ep in zip(obs_pct, eve_pct):
                pool.setdefault((a, _bin(op)), []).append(ep)
    cells = {}
    for key, ev_list in pool.items():
        if len(ev_list) < min_bin:
            continue
        ev = np.asarray(ev_list)
        cell = dict(
            median=float(np.median(ev)),
            q5=float(np.percentile(ev, 5)),
            q95=float(np.percentile(ev, 95)),
            n=len(ev),
        )
        for c in CUTS:
            cell[f"p_ge{c}"] = float(np.mean(ev >= c))
        cells[key] = cell
    return cells


def conformal_q(prepared, fit_vintages, cal_vintages, H, alpha=0.10, min_bin=20):
    """Per-age conformal radius Q_a from a fit/cal split.
    Score E = max(q5 - y, y - q95); Q_a = the (1-alpha) quantile of E (small-sample
    corrected). Widening [q5, q95] by Q_a restores ~ (1-alpha) coverage."""
    cells = fit_cells(prepared, fit_vintages, H, min_bin)
    scores = {a: [] for a in range(1, H)}
    for v in cal_vintages:
        pa = prepared[v]
        for a in range(1, H):
            obs_pct, eve_pct = pa[a]
            for op, y in zip(obs_pct, eve_pct):
                cell = cells.get((a, _bin(op)))
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
        level = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)  # conformal quantile level
        Q[a] = float(np.quantile(sc, level, method="higher"))
    return Q


def predict_interval(cell, Q_a):
    """Conformally widened 90% interval, clipped to [0, 100]."""
    lo = max(0.0, cell["q5"] - Q_a)
    hi = min(100.0, cell["q95"] + Q_a)
    return lo, hi
