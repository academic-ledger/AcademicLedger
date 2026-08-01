"""Cross-field early-signal, CORRECTED to match pipeline/early_signal_analysis.py:
AUC computed WITHIN each (subfield, vintage) cohort (>=200 papers), paper-weighted aggregate.
This removes the between-subfield inflation of the pooled version. DS is re-run as an internal
consistency check (should reproduce ~0.72/0.82/0.91/0.98 at ages 1-4)."""
import sys, json, time, urllib.request
import numpy as np
SP = sys.argv[1]; MAILTO = "ktulrich@gmail.com"
FIELDS = {"Decision Sciences": "18", "Economics & Finance": "20",
          "Biochemistry & Mol Bio": "13", "Arts & Humanities": "12"}
VINTAGES = [2010, 2011, 2012, 2013]; AGES = list(range(1, 5)); MINN = 200
PER_VINTAGE = 3500

def api(url):
    for _ in range(4):
        try:
            return json.load(urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "aL research (mailto:%s)" % MAILTO}), timeout=60))
        except Exception:
            time.sleep(2)
    return {"results": []}

def cum(d, v, age): return sum(val for y, val in d.items() if int(y) <= v + age)

def avgrank(a):
    a = np.asarray(a, float); o = a.argsort(); r = np.empty(len(a)); r[o] = np.arange(len(a))
    s = a[o]; i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]: j += 1
        if j > i: r[o[i:j + 1]] = (i + j) / 2
        i = j + 1
    return r

def auc_top(pred, ev):                       # within-cohort AUC for eventual top-10%
    ev = np.asarray(ev, float); thr = np.percentile(ev, 90); lab = (ev >= thr).astype(int)
    npos = int(lab.sum()); nneg = len(lab) - npos
    if npos == 0 or nneg == 0: return None
    r = avgrank(pred); return (r[lab == 1].sum() - npos * (npos - 1) / 2) / (npos * nneg)

out = {}
for name, fid in FIELDS.items():
    works = []
    for v in VINTAGES:
        page = 1
        while page <= max(1, PER_VINTAGE // 200):
            u = (f"https://api.openalex.org/works?filter=primary_topic.field.id:{fid},publication_year:{v}"
                 f"&select=primary_topic,publication_year,counts_by_year"
                 f"&sample={PER_VINTAGE}&seed=7&per-page=200&page={page}&mailto={MAILTO}")
            r = api(u).get("results", [])
            if not r: break
            for w in r:
                sf = (((w.get("primary_topic") or {}).get("subfield") or {}).get("id") or "").split("/")[-1]
                cby = {int(e["year"]): int(e["cited_by_count"]) for e in (w.get("counts_by_year") or [])}
                if sf: works.append((sf, w["publication_year"], cby))
            page += 1
    # cohorts by (subfield, vintage)
    cohorts = {}
    for sf, v, cby in works:
        cohorts.setdefault((sf, v), []).append(cby)
    agg = {a: {"auc": 0.0, "w": 0.0} for a in AGES}
    evall = []; ncoh = 0; npap = 0
    for (sf, v), lst in cohorts.items():
        if len(lst) < MINN: continue
        ncoh += 1; npap += len(lst)
        ev = np.array([cum(d, v, 10) for d in lst], float); evall += ev.tolist()
        for a in AGES:
            ca = np.array([cum(d, v, a) for d in lst], float)
            au = auc_top(ca, ev)
            if au is not None:
                agg[a]["auc"] += au * len(lst); agg[a]["w"] += len(lst)
    aucs = [round(agg[a]["auc"] / agg[a]["w"], 2) if agg[a]["w"] else None for a in AGES]
    evall = np.array(evall)
    out[name] = {"ncohorts": ncoh, "npapers": npap, "auc_by_age": aucs,
                 "uncited_10y": round(float(np.mean(evall == 0)), 3), "median_ev": float(np.median(evall))}
    print(f"{name:24} cohorts={ncoh:3} n={npap:6} uncited@10={out[name]['uncited_10y']:.0%} "
          f"medEv={out[name]['median_ev']:.0f} | within-cohort AUC ages1-4={aucs}", flush=True)
json.dump(out, open(SP + "/cross_field_earlysignal_v2.json", "w"), indent=1)
print("DONE-V2 -> cross_field_earlysignal_v2.json")
