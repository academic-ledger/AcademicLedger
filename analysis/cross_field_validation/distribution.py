"""Exhibit B (extended): eventual-citation distribution across four fields.
Shows, for each field, the eventual (10-year) citations at each within-field percentile — making the
uncited atom, the heavy tail, and the huge cross-field scale differences visible in one view, which is
exactly why QaL ranks (percentiles) rather than counts."""
import sys, json, time, urllib.request
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
SP = sys.argv[1]; MAILTO = "ktulrich@gmail.com"
FIELDS = [("Biochemistry & Mol Bio", "13", "#2a78d6"),
          ("Decision Sciences", "18", "#1b2a4a"),
          ("Economics & Finance", "20", "#1baf7a"),
          ("Arts & Humanities", "12", "#e8622e")]
VINTAGE = 2013; N = 6000

def api(url):
    for _ in range(4):
        try:
            return json.load(urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "aL research (mailto:%s)" % MAILTO}), timeout=60))
        except Exception:
            time.sleep(2)
    return {"results": []}

def eventual(cby):
    return sum(int(e["cited_by_count"]) for e in (cby or []) if int(e["year"]) <= VINTAGE + 10)

data = {}
for name, fid, _ in FIELDS:
    ev, page = [], 1
    while len(ev) < N and page <= N // 200:
        u = (f"https://api.openalex.org/works?filter=primary_topic.field.id:{fid},publication_year:{VINTAGE}"
             f"&select=counts_by_year&sample={N}&seed=11&per-page=200&page={page}&mailto={MAILTO}")
        r = api(u).get("results", [])
        if not r: break
        ev += [eventual(w.get("counts_by_year")) for w in r]; page += 1
    ev = np.array(ev, float)
    data[name] = {"n": len(ev), "uncited": round(float(np.mean(ev == 0)), 3),
                  "median": float(np.median(ev)), "p90": float(np.percentile(ev, 90)),
                  "p99": float(np.percentile(ev, 99)), "max": float(ev.max()),
                  "top1_share": round(float(np.sort(ev)[int(0.99 * len(ev)):].sum() / max(ev.sum(), 1)), 3),
                  "curve": [float(np.percentile(ev, p)) for p in range(0, 101)]}
    print(f"{name:24} n={len(ev):5} uncited={data[name]['uncited']:.0%} med={data[name]['median']:.0f} "
          f"p90={data[name]['p90']:.0f} p99={data[name]['p99']:.0f} top1%={data[name]['top1_share']:.0%}", flush=True)
json.dump(data, open(SP + "/cross_field_distribution.json", "w"), indent=1)

# ---- figure: eventual citations at each within-field percentile (log y), one line per field ----
plt.rcParams.update({"font.family": "DejaVu Sans"})
fig, ax = plt.subplots(figsize=(8.8, 5.4)); fig.subplots_adjust(top=0.85, bottom=0.13, left=0.10, right=0.79)
xs = list(range(0, 101))
for name, fid, col in FIELDS:
    d = data[name]; y = [v + 1 for v in d["curve"]]  # +1 so the uncited floor sits at 1 on log scale
    ax.plot(xs, y, "-", color=col, lw=2.4, label=f"{name}  ({round(d['uncited']*100)}% uncited)")
    # mark where each field lifts off zero (its uncited fraction)
    lift = int(round(d["uncited"] * 100))
    ax.plot([lift], [1], "o", color=col, ms=6)
ax.set_yscale("log")
ax.set_ylim(0.9, 3000); ax.set_xlim(0, 100)
ax.set_xlabel("within-field percentile", fontsize=12)
ax.set_ylabel("eventual citations at that percentile  (log, +1)", fontsize=12)
fig.suptitle("The same percentile means wildly different raw citations across fields",
             fontsize=13.5, color="#1b2a4a", x=0.44, y=0.965)
fig.text(0.44, 0.895, "…and half or more of every field is uncited (dots = each field's uncited share). "
         "This is why QaL ranks, not counts.", ha="center", fontsize=9.5, color="#6a6a64")
ax.grid(True, which="both", axis="y", color="#eee"); ax.set_axisbelow(True)
for s in ("top", "right"): ax.spines[s].set_visible(False)
ax.legend(fontsize=10, loc="upper left", framealpha=0.95)
fig.savefig(SP + "/fig_cross_field_distribution.png", dpi=150, facecolor="white")
print("wrote fig_cross_field_distribution.png")
