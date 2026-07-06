"""Regenerate web/public/images/fig_citation_distribution.png for the talk.

Two views of the SAME cohort — Management Science & Operations Research, published 2015
(n = 10,000), citations through the current OpenAlex snapshot, pulled straight from the DB
`works` table so the histogram reflects the real data:

  (top)    raw citations on a log axis — a smooth heavy tail (the earlier version had a spurious
           gap at ~7-19 from a binning bug; the real data decays smoothly, ~10% of papers sit there).
  (bottom) the same papers transformed to their within-cohort percentile — a flat (uniform) target,
           with the uncited papers collapsing to a single mid-rank (the "atom").

Percentile convention matches the QaL: pct(v) = 100 * (count(<v) + count(==v)/2) / N, so the whole
uncited block lands at 100 * p0 / 2.

Re-run:  PYTHONPATH=pipeline .venv/bin/python pipeline/make_fig_citation_distribution.py
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import _env; _env.load_env()
import psycopg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web", "public", "images", "fig_citation_distribution.png")
GREEN, NAVY, GREY, RED = "#2e8b57", "#1b2a4a", "#8a8a8a", "#c0392b"

with psycopg.connect(os.environ["DATABASE_URL"]) as c, c.cursor() as cur:
    cur.execute("""select w.cited_by_count from works w join subfields s on s.id=w.primary_subfield
                   where s.name='Management Science and Operations Research' and w.publication_year=2015""")
    cbc = np.array([r[0] for r in cur.fetchall()], dtype=float)

N = len(cbc)
uncited = int((cbc == 0).sum())
p_unc = uncited / N
med, mean = np.median(cbc), cbc.mean()
top1_share = cbc[cbc >= np.quantile(cbc, 0.99)].sum() / cbc.sum()
# within-cohort percentile, mid-rank (atom -> 100*p0/2)
order = np.argsort(cbc, kind="mergesort")
sc = cbc[order]
below = np.searchsorted(sc, cbc, side="left")
equal = np.searchsorted(sc, cbc, side="right") - below
pct = 100.0 * (below + equal / 2.0) / N
atom_pct = 100.0 * p_unc / 2.0
print(f"N={N}  uncited={p_unc*100:.0f}%  median={med:.0f}  mean={mean:.1f}  top1%share={top1_share*100:.0f}%  atom@{atom_pct:.0f}")

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#cccccc"})
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 10.2))
fig.subplots_adjust(top=0.90, bottom=0.10, left=0.115, right=0.955, hspace=0.34)
fig.suptitle(f"Same data, two views — Management Science & OR, 2015 cohort (n = {N:,})",
             fontsize=15.5, color=NAVY, y=0.965)

# ---- (top) raw citations, log-binned so the tail is smooth ----
cited = cbc[cbc >= 1]
# Heavy tail on a log axis is cleanest as counts-per-decade on log-log: pure log bins, log-y.
# (Count on a linear y inflates the wider tail bins into a spurious mid-range hump; log-y compresses
# that so the distribution reads as the true monotone power-law decline. Earlier version's 7-19 "gap"
# was a binning bug — the real data decays smoothly.)
bins = np.logspace(0, np.log10(cited.max()) + 0.05, 22)
ctr = np.sqrt(bins[:-1] * bins[1:])
cnt, _ = np.histogram(cited, bins=bins)
m = cnt > 0
ax1.plot(ctr[m], cnt[m], "-o", color=GREEN, ms=6, lw=2.2)
ax1.fill_between(ctr[m], cnt[m], 0.7, color=GREEN, alpha=0.12)
ax1.set_xscale("log"); ax1.set_yscale("log")
ax1.set_ylim(0.7, cnt.max() * 1.4)
ax1.set_title("Raw citations: the striking tail", fontsize=13.5, color=NAVY, pad=8)
ax1.set_xlabel("citations (log scale)", fontsize=12.5)
ax1.set_ylabel("number of papers", fontsize=12.5)
ax1.text(0.97, 0.93, f"median {med:.0f} · mean {mean:.0f}\ntop 1% hold {top1_share*100:.0f}%",
         transform=ax1.transAxes, ha="right", va="top", fontsize=12, color="#444")
ax1.tick_params(labelsize=11)
for s in ("top", "right"): ax1.spines[s].set_visible(False)

# ---- (bottom) percentile transform: flat + the atom ----
ax2.hist(pct, bins=np.arange(0, 101, 2.5), color=GREEN, edgecolor="white", linewidth=0.5)
ax2.set_title("Percentile transform: flat, plus the uncited atom", fontsize=13.5, color=NAVY, pad=8)
ax2.set_xlabel("percentile within cohort", fontsize=12.5)
ax2.set_ylabel("number of papers", fontsize=12.5)
ax2.set_xlim(0, 100)
yl = ax2.get_ylim()[1]
for x, lab in [(50, "top 50%"), (75, "25%"), (90, "10%"), (95, "5%"), (99, "1%")]:
    ax2.axvline(x, ls=(0, (5, 4)), color="#999", lw=1)
    ax2.text(x - 0.5, yl * 0.98, lab, rotation=90, ha="right", va="top", fontsize=10, color="#777")
ax2.annotate(f"~{p_unc*100:.0f}% uncited collapse\nto one rank (the atom)",
             xy=(atom_pct, yl * 0.9), xytext=(atom_pct + 12, yl * 0.62),
             fontsize=12, color=RED, ha="left",
             arrowprops=dict(arrowstyle="->", color=RED, lw=1.3))
ax2.tick_params(labelsize=11)
for s in ("top", "right"): ax2.spines[s].set_visible(False)

fig.text(0.115, 0.045, "Ranking within a (sub)field-and-year cohort turns the heavy tail into a "
         "uniform target; the only lump is the uncited atom.\nBands are the NSF percentile classes "
         "(top 50 / 25 / 10 / 5 / 1%).", ha="left", va="top", fontsize=9.5, color=GREY)

fig.savefig(OUT, dpi=150, facecolor="white")
w, h = (fig.get_size_inches() * 150).astype(int)
print(f"wrote {OUT}  ({w}x{h}px)")
