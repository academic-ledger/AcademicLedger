"""Regenerate web/public/images/fig_forecast_funnel.png for the talk slide on forecasting.

Shows the "decide late" mechanism: from NOW, each additional year of evidence gives a *conditional*
forecast of the paper's EVENTUAL (mature) percentile, and the 90% interval tightens toward the
horizon while the median barely moves. Each point is a SEPARATE conditional forecast (drawn as a
point with 90% whiskers, not a connecting line) — "the eventual percentile for papers seen at the
~94th percentile when re-observed at that age" — so it is not read as a single paper's trajectory.

ONE reference class only: Political Science & International Relations (OpenAlex subfield 3320), the
dominant 49.8% of the synthetic blend for W4287922020 "Serving Democracy" (2022, observed ~94.6th
percentile). Real calibrated numbers (calibration_models, tier "fitted", n_train=400), from NOW
(age 4, 2026) forward. The paper's actual QaL blends all 8 subfields.

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

# Political Science calibration at obs ~94th, from now (age 4) to the horizon (age 9).
more = np.array([0, 1, 2, 3, 4, 5])           # years of additional evidence beyond now
med = np.array([92.7, 92.4, 93.6, 93.6, 93.9, 93.9])
lo = np.array([89, 88, 91, 92, 93, 93])
hi = np.array([98, 97, 97, 96, 96, 95])
OBS = 94.6

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#cccccc"})
fig, ax = plt.subplots(figsize=(10, 6.4))
fig.subplots_adjust(top=0.80, bottom=0.13, left=0.10, right=0.965)
ax.grid(True, axis="y", color="#eeeeee", lw=0.9)
ax.set_axisbelow(True)

fig.suptitle("Waiting sharpens the forecast — the case for deciding late",
             fontsize=16, color=NAVY, y=0.965)
fig.text(0.5, 0.875, "One reference class: Political Science & International Relations (49.8% of this "
         "paper's blend).\nEach point is a separate conditional forecast — not a single paper's path.",
         ha="center", va="top", fontsize=11, color=GREY)

ax.axhline(OBS, ls=(0, (2, 3)), color=GREY, lw=1)
ax.text(5.55, OBS + 0.35, f"observed today: {OBS:.1f}th", fontsize=10.5, color=GREY, ha="right", va="bottom")

# each forecast = a point + 90% whiskers (deliberately NOT connected — separate conditional forecasts)
ax.errorbar(more, med, yerr=[med - lo, hi - med], fmt="o", ms=8, color=DK, ecolor=GREEN,
            elinewidth=6, capsize=8, capthick=2, alpha=0.95, label="eventual-percentile forecast (median · 90%)")

ax.annotate(f"now (age 4): [{lo[0]:.0f}, {hi[0]:.0f}]", xy=(0, hi[0]), xytext=(-0.15, 100.2),
            fontsize=12.5, color="#333", ha="left", va="top", fontweight="bold")
ax.annotate(f"horizon: [{lo[-1]:.0f}, {hi[-1]:.0f}]", xy=(5, hi[-1]), xytext=(5, 100.2),
            fontsize=12.5, color=DK, ha="right", va="top", fontweight="bold")

ax.set_xlabel("years of additional evidence (re-observe the paper later)", fontsize=13.5)
ax.set_ylabel("eventual percentile (QaL)", fontsize=13.5)
ax.set_xlim(-0.4, 5.6); ax.set_ylim(84, 101)
ax.set_xticks(more)
ax.tick_params(labelsize=11.5)
ax.legend(fontsize=11.5, loc="lower right", framealpha=0.95)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

fig.savefig(OUT, dpi=150, facecolor="white")
w, h = (fig.get_size_inches() * 150).astype(int)
print(f"wrote {OUT}  ({w}x{h}px)")
