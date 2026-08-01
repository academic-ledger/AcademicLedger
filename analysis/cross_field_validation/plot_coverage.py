"""Plot Exhibit C (definitive): honest conformal coverage vs field citation-density.
Reads coverage_results.json (produced by the in-region bulk-snapshot factory) and draws coverage per
field against the uncited fraction, with the nominal 0.90 target and the shipped [0.88,0.93] PASS band.
  python plot_coverage.py <output-dir>
"""
import sys, json
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

SP = sys.argv[1] if len(sys.argv) > 1 else "figures"
D = json.load(open("coverage_results.json"))
fields = [k for k in D if not k.startswith("_")]
fields.sort(key=lambda k: D[k]["unc"])   # dense -> sparse

plt.rcParams.update({"font.family": "DejaVu Sans"})
fig, ax = plt.subplots(figsize=(8.8, 5.4)); fig.subplots_adjust(top=0.86, bottom=0.13, left=0.10, right=0.97)

# PASS band [0.88, 0.93] and nominal 0.90
ax.axhspan(0.88, 0.93, color="#9bbf8a", alpha=0.20, zorder=0)
ax.axhline(0.90, color="#444", lw=1.1, ls="--", zorder=1)
ax.text(0.845, 0.902, "nominal 0.90", fontsize=9, color="#444", va="bottom", ha="right")
ax.text(0.415, 0.9295, "shipped PASS band  [0.88, 0.93]", fontsize=8.5, color="#3a6b28", va="top", ha="left")

x = [D[f]["unc"] / 100 for f in fields]
y = [D[f]["cov"] for f in fields]
# faint by-age spread behind each point
for f, xi in zip(fields, x):
    ba = list(D[f]["by_age"].values())
    ax.plot([xi] * len(ba), ba, marker="_", ms=13, lw=0, color=D[f]["col"], alpha=0.28, zorder=2)
ax.plot(x, y, color="#888", lw=1.0, ls="-", zorder=2, alpha=0.6)
for f, xi, yi in zip(fields, x, y):
    ax.scatter([xi], [yi], s=140, color=D[f]["col"], zorder=4, edgecolor="white", lw=1.3)
    ax.annotate(f"{f}\n{yi:.3f}", (xi, yi), textcoords="offset points",
                xytext=(0, 15), ha="center", fontsize=9, color=D[f]["col"], weight="bold")

ax.set_xlim(0.40, 0.87); ax.set_ylim(0.80, 0.945)
ax.set_xlabel("Field citation sparsity  (fraction of papers uncited at 10y)", fontsize=11)
ax.set_ylabel("Honest 90% interval coverage", fontsize=11)
ax.set_title("Exhibit C — conformal coverage holds at ~nominal across the density gradient\n"
             "leave-one-vintage-out, per (subfield x vintage) cohort; full OpenAlex snapshot",
             fontsize=11.5, loc="left")
ax.grid(axis="y", color="#ddd", lw=0.6)
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.savefig(SP + "/fig_cross_field_coverage.png", dpi=150, facecolor="white")
print("wrote", SP + "/fig_cross_field_coverage.png")
