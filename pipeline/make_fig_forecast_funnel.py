"""Regenerate web/public/images/fig_forecast_funnel.png for the talk slide on forecasting.

Shows how QaL forecasts the EVENTUAL (horizon) percentile from the evidence available NOW, and
how the 90% interval narrows as a paper ages toward maturity ("decide late"). The forecast median
barely moves; the uncertainty is what collapses.

Data = the calibrated Layer-B trajectory for W4287922020 "Serving Democracy: Voting Resource
Disparity in Florida" (2022, Political Science reference class, observed ~94.6th percentile). Pulled
from calibration_models (community 3320, obs_pct_bin 94) across age; hard-coded here so the figure is
self-contained. The paper is age 4 in 2026, where the forecast is QaL 94, 90% CI [89, 98] — matching
the live paper page.

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

age = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9])
med = np.array([90.7, 91.4, 93.7, 92.7, 92.4, 93.6, 93.6, 93.9, 93.9])
lo = np.array([81, 82, 86, 89, 88, 91, 92, 93, 93])
hi = np.array([99, 98, 100, 98, 97, 97, 96, 96, 95])
NOW = 4  # 2022 paper, viewed in 2026

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#cccccc",
                     "axes.grid": True, "grid.color": "#eeeeee"})
fig, ax = plt.subplots(figsize=(10, 6.2))
fig.subplots_adjust(top=0.88, bottom=0.13, left=0.10, right=0.965)

ax.fill_between(age, lo, hi, color=GREEN, alpha=0.18, lw=0, label="90% interval")
ax.plot(age, hi, color=GREEN, lw=1.2, alpha=0.6)
ax.plot(age, lo, color=GREEN, lw=1.2, alpha=0.6)
ax.plot(age, med, color=DK, lw=2.8, marker="o", ms=5, label="forecast median")

# "now" marker (current age) and the horizon
ax.axvline(NOW, ls=(0, (5, 4)), color="#444", lw=1.4)
ax.plot(NOW, 94.6, marker="D", ms=9, color=NAVY, zorder=5)
ax.annotate("observed today\n94.6th pctile", xy=(NOW, 94.6), xytext=(NOW - 2.6, 84.5),
            fontsize=12, color=NAVY, ha="center",
            arrowprops=dict(arrowstyle="->", color=NAVY, lw=1.2))
ax.annotate("now — age 4 (2026)\nforecast QaL 94 · [89, 98]", xy=(NOW, 98.4), xytext=(NOW + 0.25, 99.4),
            fontsize=12.5, color="#333", ha="left", va="top", fontweight="bold")
ax.annotate("horizon (maturity):\ninterval collapses → [93, 95]", xy=(9, 94), xytext=(6.6, 82.5),
            fontsize=12, color=DK, ha="left",
            arrowprops=dict(arrowstyle="->", color=DK, lw=1.2))

ax.set_title("Forecasting to the horizon: the median holds, the interval narrows",
             fontsize=16, color=NAVY, pad=12)
ax.set_xlabel("years since publication", fontsize=13.5)
ax.set_ylabel("eventual percentile (QaL)", fontsize=13.5)
ax.set_xlim(1, 9); ax.set_ylim(78, 101)
ax.tick_params(labelsize=11.5)
ax.legend(fontsize=12, loc="lower right", framealpha=0.9)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

fig.savefig(OUT, dpi=150, facecolor="white")
w, h = (fig.get_size_inches() * 150).astype(int)
print(f"wrote {OUT}  ({w}x{h}px)")
