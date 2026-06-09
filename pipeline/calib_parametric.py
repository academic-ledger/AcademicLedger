"""Parametric calibration fallback for sparse cohorts (QaL_spec.md §7 shrinkage).

The nonparametric model (calib_lib) is the production estimator and stays in charge wherever a
subfield has enough MATURED data to fit it and pass the back-test. But a subfield we've only
just begun sampling has no maturation history, so we can't fit that model — yet we still want an
honest, *labeled* estimate rather than a blank. This module supplies it from two per-subfield
parameters, each shrunk toward a discipline-level prior when the subfield is thin (§7):

  half_life : citation half-life (yrs) — how fast the eventual signal becomes visible. Sets the
              maturity ramp m(a) = g(a)/g(H), g(a) = 1 - 2^(-a/half_life), so m(H)=1.
  tail      : upper-tail heaviness of the citation distribution — modestly inflates the interval
              (heavier tails => more rank churn), recorded for transparency.

Model: assume rank persistence — the eventual percentile is centered on the observed percentile
(the unbiased estimate absent maturation data) — with an uncertainty that is wide for young
papers and narrows to near-zero at the horizon. These models are written with
confidence='parametric' and are NOT surfaced as a forecast (the UI keeps them
calibration-pending); they give the served record an honest tier and a provisional posterior
until the subfield earns 'fitted'/'gate-passed' from real matured vintages.
"""
import numpy as np

CUTS = [50, 75, 90, 95, 99]

# Discipline prior (Decision-Sciences seed default; H_HALFLIFE=6 is the project-wide global).
DISCIPLINE_PRIOR = {"half_life": 6.0, "tail": 1.0}
K0 = 200  # shrinkage strength: the prior is worth ~K0 pseudo-works


def estimate_half_life(counts_by_year_list, vintage_list):
    """Median years-to-half-citations across sampled works (the empirical citation half-life)."""
    ages = []
    for cby, v in zip(counts_by_year_list, vintage_list):
        if not cby or v is None:
            continue
        items = sorted((int(y), c) for y, c in cby.items() if int(y) >= v)
        total = sum(c for _, c in items)
        if total < 5:
            continue
        cum = 0
        for y, c in items:
            cum += c
            if cum >= total / 2.0:
                ages.append(max(1, y - v))  # age by which half the citations had arrived
                break
    return float(np.median(ages)) if ages else None


def estimate_tail(cites_list):
    """Crude upper-tail heaviness: 99th/90th citation-count ratio, normalized to ~1 for a
    typical lognormal-ish field and clipped to a sane band."""
    c = np.asarray([x for x in cites_list if x and x > 0], dtype=float)
    if len(c) < 50:
        return None
    p90, p99 = np.percentile(c, 90), np.percentile(c, 99)
    if p90 <= 0:
        return None
    return float(np.clip((p99 / p90) / 3.0, 0.3, 3.0))


def fit_params(samples, prior=DISCIPLINE_PRIOR, k0=K0):
    """samples: list of {cites, counts_by_year, vintage}. Returns shrunk params + support n."""
    n = len(samples)
    hl = estimate_half_life([s.get("counts_by_year") for s in samples],
                            [s.get("vintage") for s in samples])
    tl = estimate_tail([s.get("cites") for s in samples])
    w = n / (n + k0) if n else 0.0

    def shrink(x, p):
        return p if x is None else w * x + (1 - w) * p

    return {"half_life": round(shrink(hl, prior["half_life"]), 2),
            "tail": round(shrink(tl, prior["tail"]), 2), "n": n}


def _maturity(age, half_life, H):
    g = lambda a: 1.0 - 2.0 ** (-a / half_life)
    gH = g(H)
    return float(np.clip(g(age) / gH, 0.0, 1.0)) if gH > 0 else 1.0


def cell(age, r_obs, params, H):
    """Parametric posterior cell at (age, observed pct): {median,q5,q95,n,p_ge*}.

    A truncated-normal posterior on [0,100] centered at r_obs, whose sd is wide when the paper
    is young (low maturity) and narrows toward the horizon; the tail parameter mildly scales it.
    """
    m = _maturity(age, params["half_life"], H)
    sigma = (2.0 + 28.0 * (1.0 - m)) * (0.8 + 0.4 * params["tail"])
    grid = np.linspace(0.0, 100.0, 1001)
    dens = np.exp(-0.5 * ((grid - r_obs) / sigma) ** 2)
    s = dens.sum()
    if s <= 0:
        dens = np.ones_like(grid) / len(grid)
    else:
        dens = dens / s
    cdf = np.cumsum(dens)
    q = lambda p: float(grid[min(np.searchsorted(cdf, p), len(grid) - 1)])
    out = {"median": q(0.5), "q5": q(0.05), "q95": q(0.95), "n": int(params.get("n", 0))}
    for c in CUTS:
        out[f"p_ge{c}"] = float(dens[grid >= c].sum())
    return out
