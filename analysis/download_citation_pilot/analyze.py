#!/usr/bin/env python3
"""Download-to-citation early-signal pilot (Paper B, Result 2 — preprint pilot).

Do early PDF downloads predict eventual citations? We measure it on two preprint cohorts with open
per-article download data, as an in-domain pilot for the economics (RePEc/LogEc) study and a
replication of the classic out-of-field benchmarks:
  - Brody, Harnad & Carr (2006), arXiv physics: download->citation r ~ 0.4
  - Perneger (2004), BMJ medicine: hit->citation r ~ 0.5, plateauing by ~6 months

Cohorts (per-article monthly PDF downloads from the open Rxivist dump, Zenodo 10.5281/zenodo.7688682,
crawl frozen 2023-02; eventual citations from OpenAlex, joined by DOI):
  - medRxiv 2019 (medicine), N=913  -- pre-COVID, fully matured
  - bioRxiv 2017 (biology),  N~2500 -- a larger, longer-matured robustness cohort

This script reads the cached merged cohort (rxiv_cohort_merged.json: per paper, early downloads at
1/3/6/12 months + eventual citations) and reports the Spearman download->citation correlation at each
download window (the "plateau" curve), the atom-robust AUC for the eventual top decile, and renders
fig_download_citation.png. Rebuild the merged cohort with extract_downloads.py (needs the Rxivist dump).

Run:  ../../.venv/bin/python analyze.py
"""
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
MERGED = os.path.join(HERE, "rxiv_cohort_merged.json")
FIG = os.path.join(HERE, "fig_download_citation.png")
RESULTS = os.path.join(HERE, "results.json")
WINDOWS = [("dl1", 1), ("dl3", 3), ("dl6", 6), ("dl12", 12)]
COHORTS = [("medrxiv", "medRxiv 2019 · medicine", "#2e8b57"),
           ("biorxiv", "bioRxiv 2017 · biology", "#1b2a4a")]


def avgrank(a):
    a = np.asarray(a, float); order = a.argsort(); ranks = np.empty(len(a)); ranks[order] = np.arange(len(a))
    s = a[order]; i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + j) / 2
        i = j + 1
    return ranks


def spearman(x, y):
    rx, ry = avgrank(x), avgrank(y); rx -= rx.mean(); ry -= ry.mean()
    return float((rx * ry).sum() / np.sqrt((rx * rx).sum() * (ry * ry).sum()))


def auc(score, label):
    label = np.asarray(label); r = avgrank(score); npos = int(label.sum()); nneg = len(label) - npos
    if npos == 0 or nneg == 0:
        return float("nan")
    return float((r[label == 1].sum() - npos * (npos - 1) / 2) / (npos * nneg))


def main():
    M = json.load(open(MERGED))
    results = {}
    print(f"{'cohort':22} {'N':>5} |  ρ@1mo  ρ@3mo  ρ@6mo  ρ@12mo | AUC(top-decile, dl@6mo)")
    for key, label, _ in COHORTS:
        d = [x for x in M if x["repo"] == key]
        c = np.array([x.get("cites_best", x["cites"]) for x in d], float)   # version-of-record citations
        cpre = np.array([x["cites"] for x in d], float)                     # preprint-DOI only (conservative)
        thr = np.percentile(c, 90); top = (c >= thr).astype(int)
        rho = [spearman([x[w] for x in d], c) for w, _ in WINDOWS]
        a6 = auc([x["dl6"] for x in d], top)
        results[key] = {"N": len(d), "rho_by_window": rho, "windows": [m for _, m in WINDOWS],
                        "auc_top_decile_dl6": a6,
                        "rho_dl6_preprint": spearman([x["dl6"] for x in d], cpre),
                        "pct_published": (lambda pv: 100.0 * sum(1 for v in pv if v) / sum(1 for v in pv if v is not None)
                                          if any(v is not None for v in pv) else None)([x.get("published") for x in d]),
                        "median_cites_best": float(np.median(c)), "median_cites_preprint": float(np.median(cpre)),
                        "uncited_pct": float(np.mean(c == 0) * 100)}
        print(f"{label:22} {len(d):>5} |  " + "  ".join(f"{r:.2f}" for r in rho) + f" |  {a6:.2f}")
    json.dump(results, open(RESULTS, "w"), indent=1)

    # ---- figure: the plateau curve (ρ vs download window), with the Brody–Perneger band ----
    plt.rcParams.update({"font.family": "DejaVu Sans"})
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    fig.subplots_adjust(top=0.86, bottom=0.13, left=0.11, right=0.82)
    xs = [m for _, m in WINDOWS]
    ax.axhspan(0.40, 0.50, color="#8a8a84", alpha=0.13, lw=0)
    ax.text(12.2, 0.45, "Brody 2006 (physics)\nPerneger 2004 (medicine)", fontsize=9,
            color="#6a6a64", va="center", ha="left")
    for key, label, col in COHORTS:
        r = results[key]["rho_by_window"]
        ax.plot(xs, r, "-o", color=col, lw=2.4, ms=8, label=f"{label}  (N={results[key]['N']:,})")
        pk = int(np.argmax(r))  # annotate the peak (the level the signal reaches), not the tail
        ax.annotate(f"{r[pk]:.2f}", (xs[pk], r[pk]), textcoords="offset points", xytext=(0, 10),
                    fontsize=11, color=col, fontweight="bold", ha="center")
    ax.set_xticks(xs); ax.set_xlim(0.4, 15.5); ax.set_ylim(0, 0.6)
    ax.set_xlabel("download window (months since posting)", fontsize=12)
    ax.set_ylabel("Spearman ρ  (early downloads → eventual citations)", fontsize=12)
    fig.suptitle("Early downloads predict eventual citations — the signal is set within months",
                 fontsize=13, color="#1b2a4a", x=0.5, y=0.965)
    fig.text(0.46, 0.90, "Preprint pilot for the economics download study · early downloads → eventual citations",
             ha="center", fontsize=10.5, color="#6a6a64")
    ax.grid(True, axis="y", color="#eeeeee"); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(fontsize=10.5, loc="lower right", framealpha=0.95)
    fig.savefig(FIG, dpi=150, facecolor="white")
    print("wrote", os.path.relpath(FIG, HERE), "and", os.path.relpath(RESULTS, HERE))


if __name__ == "__main__":
    main()
