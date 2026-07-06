"""Regenerate web/public/images/fig_forecast_funnel.png for the talk slide on forecasting.

The "decide late" mechanism, one series: the paper's blended QaL forecast of its EVENTUAL (H = 10-year)
percentile. From NOW (age 4) to the horizon, the 90% interval narrows (width 9 -> 3) while the point
barely moves (93 -> 94) — more evidence sharpens the forecast, so there is no cost to deciding late.

Each marker is a SEPARATE conditional forecast (a point with 90% whiskers, not a connecting line):
"the eventual percentile for papers seen here when re-observed at that age" — not one paper's path.
The blended interval is the weighted AVERAGE of the paper's per-subfield [q5, median, q95] posteriors
(a converging pooled-rank interval), so between-subfield disagreement lives in the POINT, not the width
— which is why it collapses toward the horizon, consistent with the back-tested 10-year estimand.

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
GREEN, DK, NAVY, GREY = "#2e8b57", "#1b6b40", "#1b2a4a", "#8a8a8a"

more = np.array([0, 1, 2, 3, 4, 5])          # years of additional evidence beyond now (age 4)
med = np.array([93, 93, 93, 94, 94, 94])
lo = np.array([88, 89, 91, 92, 92, 92])
hi = np.array([97, 96, 97, 96, 96, 95])
OBS = 93.7

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#cccccc"})
fig, ax = plt.subplots(figsize=(12.5, 7.0))
fig.subplots_adjust(top=0.83, bottom=0.12, left=0.09, right=0.815)

fig.suptitle("Waiting sharpens the forecast — the case for deciding late",
             fontsize=19, color=NAVY, y=0.975, x=0.45)
fig.text(0.45, 0.90, "“Serving Democracy” (2022) — blended QaL forecast of the eventual "
         "(10-year) percentile",
         ha="center", va="top", fontsize=13, color=GREY)

ax.grid(True, axis="y", color="#eeeeee", lw=1.0)
ax.set_axisbelow(True)
ax.axhline(OBS, ls=(0, (2, 3)), color=GREY, lw=1)
ax.text(5.6, OBS, f"observed\ntoday: {OBS:.1f}", fontsize=11.5, color=GREY, ha="left", va="center")

ax.errorbar(more, med, yerr=[med - lo, hi - med], fmt="o", ms=10, color=DK, ecolor=GREEN,
            elinewidth=8, capsize=10, capthick=2.6, alpha=0.95,
            label="eventual-percentile forecast (median · 90% interval)")

ax.annotate(f"now: [{lo[0]}, {hi[0]}]   width {hi[0]-lo[0]}",
            xy=(0, hi[0]), xytext=(-0.15, hi[0] + 1.1),
            fontsize=13, color="#333", ha="left", va="bottom", fontweight="bold")
ax.annotate(f"horizon: [{lo[-1]}, {hi[-1]}]   width {hi[-1]-lo[-1]}",
            xy=(5, hi[-1]), xytext=(5.15, hi[-1] + 1.1),
            fontsize=13, color=DK, ha="right", va="bottom", fontweight="bold")

ax.set_xlabel("years of additional evidence  (re-observe the paper later)", fontsize=15)
ax.set_ylabel("eventual percentile (QaL)", fontsize=15)
ax.set_xlim(-0.45, 5.55); ax.set_ylim(84, 100)
ax.set_xticks(more)
ax.tick_params(labelsize=13)
ax.legend(fontsize=13, loc="lower right", framealpha=0.95)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

fig.savefig(OUT, dpi=150, facecolor="white")
w, h = (fig.get_size_inches() * 150).astype(int)
print(f"wrote {OUT}  ({w}x{h}px)")
