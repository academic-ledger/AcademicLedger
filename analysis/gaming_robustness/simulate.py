"""Exhibit E — gaming robustness. Simulates citation-injection attacks against QaL's Layer-A observed
standing (the exact mid-rank percentile transform of calib_lib.pct_of_all) on REAL eventual-citation
distributions per field, and quantifies how far realistic attacks move a paper.

Two data-grounded results:
  (A) Saturation cost curve — citations needed to advance +5 within-field percentile points, as a
      function of current percentile. Climbing the consequential upper tail is exponentially expensive.
  (B) Injection resistance — the percentile a target actually reaches as a function of injected
      citations k, for a consequential starting percentile; with the self-citation-discounting defense
      (a pure self-citation attack nets 0 after discounting) and an authority-weight sensitivity on
      rings (ring members are low-standing, so their citations count at weight w<1).

Input: a histogram JSON {"fid|sid|yr": {cites: freq}} (from pipeline/factory_cohorts.py or the Neon
puller). Percentiles are computed against each cohort's full empirical distribution (uncited atom
included), then averaged within field; the largest cohort per field is reported as representative.

Usage:  python simulate.py <hist.json> <out-dir>
"""
import sys, json, os
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

FIELDS = {"13": ("Biochemistry & Mol Bio", "#2a78d6"), "18": ("Decision Sciences", "#1b2a4a"),
          "20": ("Economics & Finance", "#1baf7a"), "12": ("Arts & Humanities", "#e8622e")}
GRID = np.arange(1, 99.0, 0.5)     # percentile grid
STEP = 5.0                          # "advance +5 percentile points"


class Cohort:
    """A cohort's eventual-citation distribution as an exact mid-rank percentile transform."""
    def __init__(self, hist):
        self.vals = np.array(sorted(int(k) for k in hist), dtype=float)
        self.freq = np.array([hist[str(int(v))] if str(int(v)) in hist else hist[int(v)]
                              for v in self.vals], dtype=float)
        self.N = float(self.freq.sum())
        self.cum_below = np.concatenate([[0.0], np.cumsum(self.freq)[:-1]])  # count strictly below each val

    def pct(self, x):
        """Mid-rank percentile of citation count x against the cohort (uncited atom included)."""
        i = np.searchsorted(self.vals, x)
        below = self.cum_below[i] if i < len(self.vals) and self.vals[i] == x else \
            (self.freq[:i].sum() if i > 0 else 0.0)
        eq = self.freq[i] if (i < len(self.vals) and self.vals[i] == x) else 0.0
        return 100.0 * (below + 0.5 * eq) / self.N

    def cites_at_pct(self, p):
        """Fewest citations whose mid-rank percentile reaches p (inverse of pct)."""
        pv = np.array([self.pct(v) for v in self.vals])
        idx = np.searchsorted(pv, p, side="left")
        return self.vals[min(idx, len(self.vals) - 1)]

    def standing(self, c):
        """A citer's authority = its own within-field standing in [0,1] (mid-rank percentile/100)."""
        return self.pct(c) / 100.0

    def mean_weight(self, gamma):
        """E[h(standing)] over the field's papers, h(s)=s**gamma — the average authority a citation
        carries. Uncited citers (standing≈atom mid-rank) get h(atom)**gamma; legit citers span the field."""
        s = np.array([self.pct(v) / 100.0 for v in self.vals])
        return float(np.average(s ** gamma, weights=self.freq))

    def ring_weight(self, gamma):
        """Effective citation-equivalents of ONE fabricated (uncited) ring citation under authority
        weighting: h(standing of an uncited work) / mean citation authority. <1 => rings are discounted."""
        h0 = self.standing(0.0) ** gamma
        return h0 / self.mean_weight(gamma)


def load_by_field(path):
    hist = json.load(open(path))
    by = {}
    for key, h in hist.items():
        fid = key.split("|")[0]
        if fid in FIELDS:
            by.setdefault(fid, []).append((sum(h.values()), Cohort(h)))
    return by


def saturation(by):
    """Δcitations to advance +STEP percentile points, averaged over each field's cohorts."""
    out = {}
    for fid, cohorts in by.items():
        curves = []
        for _, c in cohorts:
            cap = [c.cites_at_pct(min(p + STEP, 99.0)) - c.cites_at_pct(p) for p in GRID]
            curves.append(cap)
        out[fid] = np.mean(curves, axis=0)
    return out


def reach(cohort, start_pct, k, weight=1.0):
    """Percentile a target at start_pct reaches after injecting k citations counted at `weight`."""
    c0 = cohort.cites_at_pct(start_pct)
    return cohort.pct(c0 + weight * k)


RING = 20    # a feasible coordinated ring: 20 papers each citing the target once
GAMMA = 2.0  # authority-weight convexity h(s)=s**gamma; per-field ring discount = h(0)/mean authority


def attack_gain(by, ring=RING, gamma=GAMMA):
    """For each field's representative cohort: percentile REACHED after a fixed `ring`-citation ring,
    vs starting percentile. Two estimators:
      - count-only (no defense): each ring citation counts 1.
      - DEFENDED: self-citations discounted (a self-only attack -> 0, by construction) and the external
        ring authority-weighted — each fabricated (uncited) ring citation counts ring_weight(gamma) < 1,
        derived from the field's REAL standing distribution. Gap over y=x = percentile points stolen."""
    res = {}
    for fid, cohorts in by.items():
        _, c = max(cohorts, key=lambda t: t[0])
        w = c.ring_weight(gamma)
        res[fid] = {
            "ring_weight": w,
            "reached_countonly": [float(reach(c, p, ring, 1.0)) for p in GRID],
            "reached_defended": [float(reach(c, p, ring, w)) for p in GRID],
        }
    return res


def figA(sat, out):
    fig, ax = plt.subplots(figsize=(8.6, 5.3)); fig.subplots_adjust(bottom=0.13, left=0.11, right=0.97, top=0.88)
    for fid in [f for f in ["13", "18", "20", "12"] if f in sat]:
        name, col = FIELDS[fid]
        ax.plot(GRID, np.maximum(sat[fid], 0.5), color=col, lw=2.2, label=name)
    ax.set_yscale("log"); ax.set_xlim(50, 94); ax.set_ylim(0.5, None)   # +STEP hits the p99 ceiling past 94
    ax.axvspan(90, 94, color="#f2c94c", alpha=0.15)
    ax.text(92, ax.get_ylim()[1] * 0.5, "top\ndecile", ha="center",
            va="top", fontsize=9, color="#8a6d1a")
    ax.set_xlabel("Current within-field percentile", fontsize=11)
    ax.set_ylabel(f"Citations needed to advance +{int(STEP)} points  (log)", fontsize=11)
    ax.set_title("Exhibit E-A — percentile saturation: climbing the tail is exponentially expensive",
                 fontsize=12, loc="left")
    ax.grid(True, which="both", color="#e8e8e8", lw=0.6)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    fig.savefig(out + "/fig_gaming_saturation.png", dpi=150, facecolor="white")
    print("wrote", out + "/fig_gaming_saturation.png")


def figB(atk, out, ring=RING, gamma=GAMMA):
    fig, ax = plt.subplots(figsize=(8.6, 5.3)); fig.subplots_adjust(bottom=0.13, left=0.11, right=0.97, top=0.85)
    ax.plot(GRID, GRID, color="#999", lw=1.1, ls="--", label="no attack (y = x)")
    for fid in [f for f in ["13", "18", "20", "12"] if f in atk]:
        name, col = FIELDS[fid]
        ax.plot(GRID, atk[fid]["reached_countonly"], color=col, lw=2.2, label=name)
        ax.plot(GRID, atk[fid]["reached_defended"], color=col, lw=1.3, ls=":")
    ax.axhspan(90, 100, color="#f2c94c", alpha=0.15)
    ax.text(52, 91, "top decile", fontsize=8.5, color="#8a6d1a", va="bottom")
    ax.set_xlim(50, 98); ax.set_ylim(50, 100)
    ax.set_xlabel("Starting within-field percentile (before attack)", fontsize=11)
    ax.set_ylabel(f"Percentile reached after a {ring}-citation ring", fontsize=11)
    ax.set_title(f"Exhibit E-B — a {ring}-paper ring beats count-only QaL; the defenses blunt it in DENSE "
                 "fields, not sparse ones\n"
                 f"solid = count-only; dotted = defended (self-cites discounted + authority-weighted, γ={gamma:g})",
                 fontsize=10, loc="left")
    ax.grid(True, color="#eee", lw=0.6)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=9, loc="lower right", ncol=2)
    fig.savefig(out + "/fig_gaming_injection.png", dpi=150, facecolor="white")
    print("wrote", out + "/fig_gaming_injection.png")


def main():
    path, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    by = load_by_field(path)
    print("fields loaded:", {FIELDS[f][0]: len(c) for f, c in by.items()})
    sat = saturation(by)
    atk = attack_gain(by)
    figA(sat, out); figB(atk, out)

    res = {"ring": RING, "step": STEP, "gamma": GAMMA,
           "method": "count-only Layer A vs DEFENDED (self-citations discounted exactly; external ring "
                     "authority-weighted by citer standing h(s)=s**gamma, discount from real field distribution)",
           "fields": {}}
    for fid, cohorts in by.items():
        name = FIELDS[fid][0]
        _, c = max(cohorts, key=lambda t: t[0])
        w = c.ring_weight(GAMMA)

        def gain(p, weight):   # points a RING-citation ring steals from a paper starting at p
            return round(reach(c, p, RING, weight) - p, 1)

        res["fields"][name] = {
            "n_cohorts": len(cohorts), "rep_cohort_n": int(max(t[0] for t in cohorts)),
            "cites_at_p90": int(c.cites_at_pct(90)), "cites_at_p95": int(c.cites_at_pct(95)),
            "cites_at_p99": int(c.cites_at_pct(99)),
            "ring_weight_g1": round(c.ring_weight(1.0), 3), "ring_weight_g2": round(w, 3),
            "ring_weight_g3": round(c.ring_weight(3.0), 3),
            # a self-citation-only attack is discounted to exactly 0 gain, by construction (all weights):
            "selfcite_only_gain": 0.0,
            # external-ring points stolen: count-only vs defended (authority-weighted g2)
            "ring_gain_p50_countonly": gain(50, 1.0), "ring_gain_p50_defended": gain(50, w),
            "ring_gain_p75_countonly": gain(75, 1.0), "ring_gain_p75_defended": gain(75, w),
            "ring_gain_p90_countonly": gain(90, 1.0), "ring_gain_p90_defended": gain(90, w),
        }
    json.dump(res, open(out + "/gaming_results.json", "w"), indent=1)
    print("wrote", out + "/gaming_results.json")
    for nm, d in res["fields"].items():
        print(f"  {nm:24} p95={d['cites_at_p95']} p99={d['cites_at_p99']} | 20-ring @p75 steals "
              f"+{d['ring_gain_p75_countonly']} (count-only) -> +{d['ring_gain_p75_defended']} (defended, "
              f"w={d['ring_weight_g2']})")


if __name__ == "__main__":
    main()
