"""Regenerate web/public/images/fig_early_signal.png for the talk's "decide late" evidence slide.

Empirical proof that early citations predict a paper's EVENTUAL (10-year) within-cohort rank —
computed on the QaL's own back-tested calibration sample: the three Decision-Sciences subfields
(Management Science & Operations Research, Information Systems & Management, General Decision
Sciences), publication years 2008-2015, ~302,000 papers with OpenAlex counts_by_year. For each
(subfield, vintage) cohort >=200 papers we cumulate citations at each age and at the 10-year
horizon, then aggregate (paper-weighted) three curves vs age:

  - rank correlation (Spearman rho) between the age-k count and the eventual count
  - AUC for picking out the eventual top decile from the age-k count  (atom-robust: it ignores
    the huge tied-at-zero mass, so unlike Spearman it isn't inflated by (0,0) concordances, and
    unlike Kendall tau-b it isn't structurally floored by the ties)
  - share of eventual citations already accrued

The story: early citations pick out the eventual top decile well before the full ranking or the
citation total matures. At year 1, 88% of papers are uncited and ~53% of the eventual top decile
are still invisible; the signal is real but slow. Real signal early, full picture late — the
empirical case for deciding late. (Recompute: scratchpad/early_signal_mf.py against the DB.)

Re-run:  .venv/bin/python pipeline/make_fig_early_signal.py   (requires matplotlib)
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web", "public", "images", "fig_early_signal.png")
GREEN, NAVY, GREY, DK = "#2e8b57", "#1b2a4a", "#8a8a8a", "#1b6b40"

age = np.arange(1, 10)
rho = np.array([0.388, 0.570, 0.732, 0.883, 0.924, 0.950, 0.967, 0.981, 0.991]) * 100
auc = np.array([0.715, 0.820, 0.906, 0.981, 0.991, 0.995, 0.997, 0.998, 0.999]) * 100
accr = np.array([5.1, 11.8, 20.8, 32.0, 43.3, 54.8, 66.1, 77.4, 88.9])

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#cccccc"})
fig, ax = plt.subplots(figsize=(12.5, 7.4))
fig.subplots_adjust(top=0.86, bottom=0.19, left=0.085, right=0.965)

fig.suptitle("How late must you decide?  Early citations vs. eventual standing",
             fontsize=19, color=NAVY, y=0.975, x=0.52)
fig.text(0.52, 0.905, "Every matured paper in the QaL's three back-tested subfields "
         "(~302,000; Decision Sciences, 2008–2015)", ha="center", va="top", fontsize=12.5, color=GREY)

ax.grid(True, axis="y", color="#eeeeee", lw=1.0); ax.set_axisbelow(True)
ax.plot(age, auc, "-", color=NAVY, lw=3.2, marker="s", ms=8, label="picks out the eventual top 10%  (AUC)")
ax.plot(age, rho, "-", color=GREEN, lw=3.2, marker="o", ms=8, label="ranks the whole field  (Spearman ρ)")
ax.plot(age, accr, ":", color=GREY, lw=3.0, marker="^", ms=8, label="eventual citations accrued")

# the atom + the 2-year read
ax.annotate("year 1: 88% of papers uncited;\n53% of the eventual top 10% still invisible",
            xy=(1, rho[0]), xytext=(1.35, 46), fontsize=12, color="#555", ha="left",
            arrowprops=dict(arrowstyle="->", color="#999", lw=1.2))
ax.axvline(2, color="#e2e2e2", lw=1.2, zorder=0)
ax.text(2.15, 14, "by year 2:  AUC 0.82 · ρ 0.57 · 12% of citations in", fontsize=11.5, color="#555", va="bottom")

ax.set_xlabel("years after publication  (eventual = 10-year citations)", fontsize=15)
ax.set_ylabel("percent", fontsize=15)
ax.set_xlim(0.7, 9.3); ax.set_ylim(0, 103)
ax.set_xticks(age); ax.set_yticks(range(0, 101, 20))
ax.set_yticklabels([f"{v}%" for v in range(0, 101, 20)])
ax.tick_params(labelsize=13)
ax.legend(fontsize=13, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3,
          frameon=False, handletextpad=0.6, columnspacing=2.4)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

fig.savefig(OUT, dpi=150, facecolor="white")
w, h = (fig.get_size_inches() * 150).astype(int)
print(f"wrote {OUT}  ({w}x{h}px)")
