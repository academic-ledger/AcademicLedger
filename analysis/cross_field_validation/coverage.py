"""Exhibit C (extended): cross-field calibration coverage.
Runs the EXACT shipped back-test (pipeline/backtest.py: honest leave-one-vintage-out, conformalized
90% interval) per field, reusing calib_lib. Question: do QaL's 90% intervals cover ~90% of realized
eventual percentiles in Economics, Biochemistry, and — especially — Arts & Humanities?"""
import sys, json, time, urllib.request
import numpy as np
sys.path.insert(0, "/Users/ulrich/projects/academic-ledger/pipeline")
import calib_lib as cl
SP = sys.argv[1]; MAILTO = "ktulrich@gmail.com"
FIELDS = {"Biochemistry & Mol Bio": "13", "Decision Sciences": "18",
          "Economics & Finance": "20", "Arts & Humanities": "12"}
VINTAGES = [2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015]; H = 10; PER = 5000; MINN = 200

def api(url):
    for _ in range(4):
        try:
            return json.load(urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "aL research (mailto:%s)" % MAILTO}), timeout=60))
        except Exception:
            time.sleep(2)
    return {"results": []}

def conformal_from_train(prepared, train_vintages, H):
    """Per-age conformal radius from train vintages only (inner LOO) — copied from backtest.py."""
    pooled = {a: [] for a in range(1, H)}
    for held in train_vintages:
        fit_v = [v for v in train_vintages if v != held]
        cells = cl.fit_cells(prepared, fit_v, H)
        pa = prepared[held]
        for a in range(1, H):
            obs_pct, eve_pct = pa[a]
            for op, y in zip(obs_pct, eve_pct):
                cell = cl.predict_cell(cells, a, op)
                if cell is not None:
                    pooled[a].append(max(cell["q5"] - y, y - cell["q95"]))
    Q = {}
    for a, sc in pooled.items():
        if sc:
            sc = np.asarray(sc); n = len(sc); level = min(1.0, np.ceil((n + 1) * 0.90) / n)
            Q[a] = float(np.quantile(sc, level, method="higher"))
        else:
            Q[a] = 0.0
    return Q

out = {}
for name, fid in FIELDS.items():
    # pull cohorts: subfield + counts_by_year, per vintage
    cohorts = {}   # (subfield, vintage) -> [cby dict]
    for v in VINTAGES:
        page = 1
        while page <= PER // 200:
            u = (f"https://api.openalex.org/works?filter=primary_topic.field.id:{fid},publication_year:{v}"
                 f"&select=primary_topic,counts_by_year&sample={PER}&seed=13&per-page=200&page={page}&mailto={MAILTO}")
            r = api(u).get("results", [])
            if not r: break
            for w in r:
                sf = (((w.get("primary_topic") or {}).get("subfield") or {}).get("id") or "").split("/")[-1]
                if not sf: continue
                cby = {int(e["year"]): int(e["cited_by_count"]) for e in (w.get("counts_by_year") or [])}
                cohorts.setdefault((sf, v), []).append(cby)
            page += 1
    # build prepared_by_comm (subfield -> {vintage: prepared}), subfields with >=3 vintages of >=MINN
    by_sf = {}
    for (sf, v), lst in cohorts.items():
        if len(lst) >= MINN:
            by_sf.setdefault(sf, {})[v] = cl.prepare(lst, v, H)
    prepared_by_comm = {sf: pv for sf, pv in by_sf.items() if len(pv) >= 3}
    # coverage: honest LOO, exactly as backtest.py
    overall = [0, 0]; by_age = {a: [0, 0] for a in range(1, H)}
    for sf, prepared in prepared_by_comm.items():
        vints = list(prepared.keys())
        for test_v in vints:
            train = [v for v in vints if v != test_v]
            Q = conformal_from_train(prepared, train, H)
            cells = cl.fit_cells(prepared, train, H)
            pa = prepared[test_v]
            for a in range(1, H):
                obs_pct, eve_pct = pa[a]
                for op, y in zip(obs_pct, eve_pct):
                    cell = cl.predict_cell(cells, a, op)
                    if cell is None: continue
                    lo, hi = cl.predict_interval(cell, Q.get(a, 0.0))
                    hit = 1 if lo <= y <= hi else 0
                    overall[0] += hit; overall[1] += 1
                    by_age[a][0] += hit; by_age[a][1] += 1
    cov = overall[0] / overall[1] if overall[1] else float("nan")
    ba = {a: round(by_age[a][0] / by_age[a][1], 3) for a in range(1, H) if by_age[a][1]}
    out[name] = {"coverage": round(cov, 3), "n": overall[1], "n_subfields": len(prepared_by_comm), "by_age": ba}
    print(f"{name:24} coverage={cov:.3f}  n={overall[1]:6}  subfields={len(prepared_by_comm)}  "
          f"by_age(1,3,5,9)={[ba.get(a) for a in (1,3,5,9)]}", flush=True)
json.dump(out, open(SP + "/cross_field_coverage.json", "w"), indent=1)
print("DONE-COVERAGE")
