"""Regenerate web/public/images/fig_forecast_funnel.png for the talk slide on forecasting.

Two STACKED panels that together make the confidence-interval point — where does the width of a
QaL forecast come from, and does waiting remove it?

  (a) ONE reference class: Political Science & International Relations (OpenAlex subfield 3320),
      the paper's dominant 37.7% subfield, observed at the 97.8th percentile there. From NOW
      (age 4) to the horizon, the 90% interval collapses [95,100] -> [98,98]: within a well-defined
      field, more evidence sharpens the forecast almost to a point.
  (b) The paper's ACTUAL QaL, blended over all 9 subfields it spans. The point estimate firms up
      (93 -> 94) but the 90% interval stays wide (~[77,99] -> [80,99], width 22 -> 19): the subfields
      disagree (86th-98th), and that reference-class ambiguity is IRREDUCIBLE — waiting cannot close it.

Both panels share a y-axis so the width contrast is directly comparable. Each point is a SEPARATE
conditional forecast (drawn as a point with 90% whiskers, not a connecting line): "the eventual
percentile for papers seen here when re-observed at that age" — not a single paper's trajectory.

Real calibrated numbers (calibration_models, tier "fitted"), for W4287922020 "Serving Democracy"
(2022, blended observed 93.7th), from NOW (age 4, 2026) forward.

Re-run:  .venv/bin/python pipeline/make_fig_forecast_funnel.py   (requires matplotlib)
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web", "public", "images", "fig_forecast_funnel.png")
GREEN, DK, NAVY, GREY, AMBER = "#2e8b57", "#1b6b40", "#1b2a4a", "#8a8a8a", "#b8860b"

more = np.array([0, 1, 2, 3, 4, 5])          # years of additional evidence beyond now (age 4)

# (a) Political Science subfield, observed ~97.8th: the interval collapses.
medA = np.array([97.3, 97.6, 97.7, 97.7, 97.8, 98.0])
loA = np.array([95, 96, 96, 97, 97, 98]);  hiA = np.array([100, 99, 99, 99, 99, 98])
OBS_A = 97.8
# (b) Blended over 9 subfields: the point firms up, the interval stays wide.
ptB = np.array([93, 93, 93, 94, 94, 94])
loB = np.array([77, 77, 78, 78, 78, 80]);  hiB = np.array([99, 99, 99, 99, 99, 99])
OBS_B = 93.7

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#cccccc"})
fig, (axA, axB) = plt.subplots(2, 1, figsize=(9.5, 10.6), sharex=True)
fig.subplots_adjust(top=0.85, bottom=0.085, left=0.105, right=0.965, hspace=0.32)

fig.suptitle("Two sources of forecast uncertainty — and only one shrinks with age",
             fontsize=16.5, color=NAVY, y=0.975)
fig.text(0.5, 0.923, "“Serving Democracy” (2022) — forecasts from now (age 4) to a 5-year horizon",
         ha="center", va="top", fontsize=12, color=GREY)


def panel(ax, med, lo, hi, obs, ec, obs_lab, ttl, tcol):
    ax.grid(True, axis="y", color="#eeeeee", lw=0.9)
    ax.set_axisbelow(True)
    ax.axhline(obs, ls=(0, (2, 3)), color=GREY, lw=1)
    ax.text(5.5, obs + 0.5, obs_lab, fontsize=10.5, color=GREY, ha="right", va="bottom")
    ax.errorbar(more, med, yerr=[med - lo, hi - med], fmt="o", ms=8, color=DK, ecolor=ec,
                elinewidth=6, capsize=8, capthick=2, alpha=0.95)
    ax.annotate(f"now: [{lo[0]:.0f}, {hi[0]:.0f}]  (width {hi[0]-lo[0]:.0f})",
                xy=(0, hi[0]), xytext=(-0.15, hi[0] + 1.4),
                fontsize=11.5, color="#333", ha="left", va="bottom", fontweight="bold")
    ax.annotate(f"horizon: [{lo[-1]:.0f}, {hi[-1]:.0f}]  (width {hi[-1]-lo[-1]:.0f})",
                xy=(5, hi[-1]), xytext=(5.15, hi[-1] + 1.4),
                fontsize=11.5, color=tcol, ha="right", va="bottom", fontweight="bold")
    ax.set_title(ttl, fontsize=13.5, color=tcol, pad=9, loc="left")
    ax.set_ylabel("eventual percentile (QaL)", fontsize=12.5)
    ax.set_ylim(74, 103)
    ax.tick_params(labelsize=11)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


panel(axA, medA, loA, hiA, OBS_A, GREEN,
      f"observed in this field: {OBS_A:.1f}th",
      "(a) One reference class (Political Science): the interval collapses as evidence accrues",
      DK)
panel(axB, ptB, loB, hiB, OBS_B, AMBER,
      f"blended observed today: {OBS_B:.1f}th",
      "(b) The paper's QaL, blended over 9 disagreeing subfields: the interval stays wide",
      "#8a5a00")

axB.set_xlabel("years of additional evidence (re-observe the paper later)", fontsize=13)
axB.set_xlim(-0.4, 5.6); axB.set_xticks(more)

fig.savefig(OUT, dpi=150, facecolor="white")
w, h = (fig.get_size_inches() * 150).astype(int)
print(f"wrote {OUT}  ({w}x{h}px)")
