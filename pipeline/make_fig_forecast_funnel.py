"""Regenerate web/public/images/fig_forecast_funnel.png for the talk slide on forecasting.

ONE wide panel, two series side by side (dodged) at each age, to make the confidence-interval
point directly comparable — where does the width of a QaL forecast come from, and does waiting
remove it?

  GREEN — ONE reference class: Political Science & International Relations (OpenAlex subfield 3320),
      the paper's dominant 37.7% subfield, observed at the 97.8th percentile there. From NOW
      (age 4) to the horizon, the 90% interval collapses [95,100] -> [98,98]: within a well-defined
      field, more evidence sharpens the forecast almost to a point.
  AMBER — the paper's ACTUAL QaL, blended over all 9 subfields it spans. The point estimate firms
      up (93 -> 94) but the 90% interval stays wide (~[77,99] -> [80,99], width 22 -> 19): the
      subfields disagree (86th-98th), and that reference-class ambiguity is IRREDUCIBLE — waiting
      cannot close it.

Each marker is a SEPARATE conditional forecast (a point with 90% whiskers, not a connecting line):
"the eventual percentile for papers still seen here when re-observed at that age" — not one paper's
trajectory. The single-field median drifts up (97.3 -> 97.9) as regression to the mean burns off with
a more reliable, older observation.

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
GREEN, DK, NAVY, GREY, AMBER, DKAMBER = "#2e8b57", "#1b6b40", "#1b2a4a", "#8a8a8a", "#d19a1a", "#8a5a00"

more = np.array([0, 1, 2, 3, 4, 5])          # years of additional evidence beyond now (age 4)

# GREEN: Political Science subfield, observed ~97.8th — the interval collapses.
medA = np.array([97.3, 97.6, 97.7, 97.7, 97.8, 98.0])
loA = np.array([95, 96, 96, 97, 97, 98]);  hiA = np.array([100, 99, 99, 99, 99, 98])
OBS_A = 97.8
# AMBER: blended over 9 subfields — the point firms up, the interval stays wide.
ptB = np.array([93, 93, 93, 94, 94, 94])
loB = np.array([77, 77, 78, 78, 78, 80]);  hiB = np.array([99, 99, 99, 99, 99, 99])
OBS_B = 93.7

DODGE = 0.14
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#cccccc"})
fig, ax = plt.subplots(figsize=(13, 7.8))
fig.subplots_adjust(top=0.83, bottom=0.185, left=0.085, right=0.835)

fig.suptitle("Two sources of forecast uncertainty — and only one shrinks with age",
             fontsize=19, color=NAVY, y=0.975, x=0.46)
fig.text(0.46, 0.905, "“Serving Democracy” (2022) — forecasts from now (age 4) to a 5-year horizon",
         ha="center", va="top", fontsize=13.5, color=GREY)

ax.grid(True, axis="y", color="#eeeeee", lw=1.0)
ax.set_axisbelow(True)

# faint reference lines for each series' observed-today value
ax.axhline(OBS_A, ls=(0, (2, 3)), color=GREEN, lw=1, alpha=0.55)
ax.axhline(OBS_B, ls=(0, (2, 3)), color=DKAMBER, lw=1, alpha=0.5)

ax.errorbar(more - DODGE, medA, yerr=[medA - loA, hiA - medA], fmt="o", ms=9, color=DK, ecolor=GREEN,
            elinewidth=7, capsize=9, capthick=2.4, alpha=0.95,
            label="One field (Political Science) — collapses to a point")
ax.errorbar(more + DODGE, ptB, yerr=[ptB - loB, hiB - ptB], fmt="o", ms=9, color=DKAMBER, ecolor=AMBER,
            elinewidth=7, capsize=9, capthick=2.4, alpha=0.95,
            label="Blended over 9 disagreeing subfields — stays wide")

# width call-outs at NOW and HORIZON for each series
ax.annotate(f"width {hiA[0]-loA[0]:.0f}", xy=(-DODGE, hiA[0]), xytext=(-DODGE, hiA[0] + 0.7),
            fontsize=12, color=DK, ha="center", va="bottom", fontweight="bold")
ax.annotate(f"width {hiA[-1]-loA[-1]:.0f}", xy=(5 - DODGE, hiA[-1]), xytext=(5 - DODGE, hiA[-1] + 0.9),
            fontsize=12, color=DK, ha="center", va="bottom", fontweight="bold")
ax.annotate(f"width {hiB[0]-loB[0]:.0f}", xy=(DODGE, loB[0]), xytext=(DODGE, loB[0] - 0.8),
            fontsize=12, color=DKAMBER, ha="center", va="top", fontweight="bold")
ax.annotate(f"width {hiB[-1]-loB[-1]:.0f}", xy=(5 + DODGE, loB[-1]), xytext=(5 + DODGE, loB[-1] - 0.8),
            fontsize=12, color=DKAMBER, ha="center", va="top", fontweight="bold")

ax.text(5.62, OBS_A, f"observed in\nPolitical Sci: {OBS_A:.1f}", fontsize=11.5, color=GREEN,
        ha="left", va="center")
ax.text(5.62, OBS_B, f"blended\nobserved: {OBS_B:.1f}", fontsize=11.5, color=DKAMBER,
        ha="left", va="center")

ax.set_xlabel("years of additional evidence  (re-observe the paper later)", fontsize=15)
ax.set_ylabel("eventual percentile (QaL)", fontsize=15)
ax.set_xlim(-0.55, 5.55); ax.set_ylim(74, 103)
ax.set_xticks(more)
ax.tick_params(labelsize=13)
ax.legend(fontsize=12.5, loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=2,
          frameon=False, handletextpad=0.6, columnspacing=2.0)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

fig.savefig(OUT, dpi=150, facecolor="white")
w, h = (fig.get_size_inches() * 150).astype(int)
print(f"wrote {OUT}  ({w}x{h}px)")
