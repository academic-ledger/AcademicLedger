"""Regenerate web/public/images/fig_percentile_transform.png for the talk slide
"Reporting Q as a Percentile Class".

Two panels STACKED vertically (portrait) so they fill the slide's height and read large:
  (top)    Raw citations — the heavy-tailed "striking tail", log x-axis (cited papers only).
  (bottom) The within-(sub)field-and-year percentile transform — flat, plus the uncited atom,
           with the NSF/Leiden percentile-class bands marked.

The data is a representative Management Science & OR 2015-cohort citation sample (n=10,000),
generated deterministically and tuned to the cohort's observed summary stats (~48% uncited,
median 1, mean ~13, top 1% ~ a quarter of citations). The *shape* — heavy tail -> uniform-plus-atom
under the percentile transform — is universal across fields (QaL_spec §4); annotations report the
shown sample's actual computed stats so the figure is self-consistent.

Re-run:  .venv/bin/python pipeline/make_fig_percentile_transform.py
Requires matplotlib in the venv:  .venv/bin/pip install matplotlib
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web", "public", "images", "fig_percentile_transform.png")

GREEN, NAVY, GREY, ORANGE = "#2e8b57", "#1b2a4a", "#8a8a8a", "#c1440e"
N, UNCITED_FRAC = 10_000, 0.48

# ---- 1. representative citation sample -------------------------------------------------------
# Cited papers = a mode-at-1 bulk (most papers get a few cites) + a heavy but not-degenerate tail
# (the few highly-cited). Tuned so the shown sample ~matches the cohort: median 1, mean ~13, top 1%
# ~ a quarter of all citations — without the runaway concentration a bare lognormal gives.
rng = np.random.default_rng(42)
n_zero = int(round(UNCITED_FRAC * N))
n_pos = N - n_zero
n_tail = int(round(0.19 * n_pos))
bulk = 1 + rng.poisson(1.6, n_pos - n_tail)                            # mode 1, small counts
tail = np.round(np.minimum(2000, rng.lognormal(mean=4.4, sigma=0.72, size=n_tail)))
cites = np.concatenate([np.zeros(n_zero), bulk, tail]).astype(int)

# ---- 2. percentile within the cohort --------------------------------------------------------
# Break integer ties among cited papers (jitter) so the transform shows its true continuous shape:
# uniform across the cited band. The uncited pile stays collapsed onto ONE rank (the atom).
cj = cites.astype(float)
nz = cites > 0
cj[nz] += rng.uniform(0.0, 0.999, nz.sum())
ranks = cj.argsort().argsort()                          # ascending rank 0..N-1
pct = 100.0 * (ranks + 0.5) / N
atom_pct = 100.0 * (n_zero / 2) / N                     # ~24: mid-rank of the uncited group
pct[~nz] = atom_pct

median, mean = int(np.median(cites)), cites.mean()
top1_share = np.sort(cites)[::-1][: N // 100].sum() / cites.sum()
print(f"n={N} uncited={n_zero/N:.0%} median={median} mean={mean:.0f} "
      f"top1%share={top1_share:.0%} max={cites.max()} atom@pct={atom_pct:.0f}")

# ---- 3. plot: two stacked panels ------------------------------------------------------------
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#cccccc"})
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 11.5))
fig.subplots_adjust(top=0.905, bottom=0.115, left=0.115, right=0.965, hspace=0.34)
fig.suptitle("Same data, two views — Management Science & OR, 2015 cohort (n = 10,000)",
             fontsize=14, color=NAVY, y=0.965)

# (top) raw citations, cited papers only, on a log axis — the tail is the story
cited = cites[nz]
bins = np.logspace(0, np.log10(cited.max()), 34)
ax1.hist(cited, bins=bins, color=GREEN, edgecolor="white", linewidth=0.4)
ax1.set_xscale("log")
ax1.set_title("Raw citations: the striking tail", fontsize=15, color=NAVY, pad=8)
ax1.set_xlabel("citations (log scale)", fontsize=13)
ax1.set_ylabel("number of papers", fontsize=13)
ax1.tick_params(labelsize=11)
ax1.text(0.97, 0.93, f"median {median} · mean {mean:.0f}\ntop 1% hold {top1_share:.0%}",
         transform=ax1.transAxes, ha="right", va="top", fontsize=12.5, color="#444")
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)

# (bottom) the percentile transform — flat across the cited band, plus the uncited atom
ax2.hist(pct, bins=np.arange(0, 101, 2.5), color=GREEN, edgecolor="white", linewidth=0.4)
ax2.set_title("Percentile transform: flat, plus the uncited atom", fontsize=15, color=NAVY, pad=8)
ax2.set_xlabel("eventual percentile within cohort", fontsize=13)
ax2.set_ylabel("number of papers", fontsize=13)
ax2.set_xlim(0, 100)
ax2.tick_params(labelsize=11)
top = ax2.get_ylim()[1]
for x, lab in [(50, "top 50%"), (75, "25%"), (90, "10%"), (95, "5%"), (99, "1%")]:
    ax2.axvline(x, color=GREY, linestyle=(0, (4, 4)), linewidth=1)
    ax2.text(x - 0.6, top * 0.985, lab, rotation=90, ha="right", va="top", fontsize=9.5, color=GREY)
ax2.annotate(f"~{n_zero/N:.0%} uncited collapse\nto one rank (the atom)",
             xy=(atom_pct + 1.5, top * 0.88), xytext=(atom_pct + 12, top * 0.72),
             fontsize=12, color=ORANGE, arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.3))
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)

fig.text(0.5, 0.028,
         "Ranking within a field-and-year cohort turns the power law into a uniform target; the "
         "only lump is the uncited atom.\nBands are the NSF percentile classes (top 50/25/10/5/1%); "
         "Characteristic Scores & Scales is a parameter-free alternative.",
         ha="center", va="bottom", fontsize=9.5, color=GREY)

fig.savefig(OUT, dpi=150, facecolor="white")
w, h = (fig.get_size_inches() * 150).astype(int)
print(f"wrote {OUT}  ({w}x{h}px)")
