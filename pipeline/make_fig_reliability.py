"""Regenerate web/public/images/fig_reliability.png for the talk slide on peer-review reliability.

Two panels STACKED vertically (portrait) so they read large beside the slide text:
  (a) Reliability of the aggregate verdict vs. number of reviewers (Spearman–Brown), for three
      single-review reliabilities R1 (0.34 meta-analysis mean, 0.30, 0.20 grant review).
  (b) Probability a paper truly at distance d from the accept/reject bar is misclassified, vs.
      number of reviewers, for d = 0.25 / 0.5 / 1.0. A borderline paper (d = 0.5) needs ~11
      reviewers to get under 5% error — consistent with the slide's ">10 judges" point.

Illustrative model (QaL_spec "A Simple Model"; ICC ≈ 0.34): each reviewer sees q0 through noise;
the k-reviewer aggregate follows Spearman–Brown. Panel (b) uses misclass = Phi(-d*sqrt(k)): a paper
d SDs from the bar is called wrong with prob Phi(-d*sqrt(k)); d=0.5 crosses 5% at k≈11.

Re-run:  .venv/bin/python pipeline/make_fig_reliability.py   (requires matplotlib)
"""
import math
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web", "public", "images", "fig_reliability.png")

GREEN, BLUE, RED, PURPLE, NAVY, GREY = "#2e8b57", "#2166ac", "#b2182b", "#762a83", "#1b2a4a", "#8a8a8a"
Phi = np.vectorize(lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2))))

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#cccccc",
                     "axes.grid": True, "grid.color": "#ececec"})
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 11.5))
fig.subplots_adjust(top=0.955, bottom=0.06, left=0.115, right=0.965, hspace=0.26)

# ---- (a) Spearman–Brown reliability of the aggregate verdict --------------------------------
k = np.arange(1, 21)
for R1, c, lab in [(0.34, GREEN, "R₁ = 0.34 (meta-analysis mean)"),
                   (0.30, BLUE, "R₁ = 0.30"),
                   (0.20, RED, "R₁ = 0.20 (grant review)")]:
    ax1.plot(k, k * R1 / (1 + (k - 1) * R1), color=c, lw=2.6, label=lab)
ax1.axhline(0.8, ls=(0, (5, 4)), color="#444", lw=1.2)
ax1.text(3.6, 0.82, '"acceptable" reliability 0.8', ha="left", va="bottom", fontsize=11, color="#444")
ax1.axvspan(2, 3, color="#999", alpha=0.18, lw=0)
ax1.text(2.5, 0.03, "current\n(2–3)", ha="center", va="bottom", fontsize=10.5, color="#555")
ax1.set_title("(a) Reliability vs number of reviewers (Spearman–Brown)", fontsize=14, color=NAVY, pad=8)
ax1.set_xlabel("Number of independent reviewers", fontsize=12.5)
ax1.set_ylabel("Reliability of the aggregate verdict", fontsize=12.5)
ax1.set_xlim(1, 20); ax1.set_ylim(0, 1.0)
ax1.tick_params(labelsize=11)
ax1.legend(fontsize=11, loc="lower right", framealpha=0.9)
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)

# ---- (b) misclassification of a paper near the bar ------------------------------------------
kk = np.linspace(1, 20, 200)
for d, c, lab in [(0.25, RED, "d = 0.25 (close call)"),
                  (0.5, PURPLE, "d = 0.5 (typical borderline)"),
                  (1.0, GREEN, "d = 1.0 (clear case)")]:
    ax2.plot(kk, 100 * Phi(-d * np.sqrt(kk)), color=c, lw=2.6, label=lab)
ax2.axhline(5, ls=(0, (5, 4)), color="#444", lw=1.2)
ax2.text(19.7, 6.2, "5% error", ha="right", va="bottom", fontsize=11, color="#444")
ax2.axvspan(2, 3, color="#999", alpha=0.18, lw=0)
ax2.text(2.5, 47, "current\n(2–3)", ha="center", va="top", fontsize=10.5, color="#555")
ax2.annotate("d = 0.5 needs ~11 reviewers\nfor 5% error", xy=(11, 5), xytext=(12.5, 17),
             fontsize=11.5, color=PURPLE, ha="left",
             arrowprops=dict(arrowstyle="->", color=PURPLE, lw=1.3))
ax2.set_title("(b) Misclassification of a paper near the bar", fontsize=14, color=NAVY, pad=8)
ax2.set_xlabel("Number of independent reviewers", fontsize=12.5)
ax2.set_ylabel("Probability of a wrong accept/reject (%)", fontsize=12.5)
ax2.set_xlim(1, 20); ax2.set_ylim(0, 50)
ax2.tick_params(labelsize=11)
ax2.legend(fontsize=11, loc="upper right", framealpha=0.9)
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)

fig.savefig(OUT, dpi=150, facecolor="white")
w, h = (fig.get_size_inches() * 150).astype(int)
print(f"wrote {OUT}  ({w}x{h}px)")
