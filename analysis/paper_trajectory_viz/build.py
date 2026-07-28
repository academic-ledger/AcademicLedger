#!/usr/bin/env python3
"""Regenerate the "A growth chart for a paper" research note (web/public/research-note.html).

Pipeline: pull a matured Management Science & OR cohort from Neon -> compute the citation
percentile bands, the within-field percentile trajectories, and the empirical eventual-percentile
forecast fan -> inject into template.html -> write the hosted page.

Every number is real. Cohort: OpenAlex subfield 1803 (Mgmt Sci & OR), publication years 2011-2014,
pooled by paper age, a deterministic 25% hash sample (bands are stable at this size). Cumulative
citations come from OpenAlex counts_by_year; the percentile is a full-population mid-rank within the
cohort at each age; the forecast interval is the empirical 5/50/95th percentile of eventual (age-10)
standing among papers with the same observed citations at that age -- the back-tested core of QaL's
Layer B (production adds a conformal correction for guaranteed coverage).

Usage:
    PYTHONPATH=../../pipeline ../../.venv/bin/python build.py           # pull from DB + rebuild
    ../../.venv/bin/python build.py --no-pull                          # rebuild page from cached JSON
"""
import os, re, sys, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA_JSON = os.path.join(HERE, "trajectory_viz_data.json")
TEMPLATE = os.path.join(HERE, "template.html")
OUT_PAGE = os.path.join(ROOT, "web", "public", "research-note.html")

SUBFIELD = "1803"
YEARS = (2011, 2014)
SAMPLE_PCT = 25          # deterministic hash sample
AGES = list(range(1, 11))
BAND_PS = [50, 75, 90, 95, 99]
FAN_EDGES = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 10**9]


def pull():
    try:
        import _env; _env.load_env()      # pipeline/_env.py, if on PYTHONPATH
    except Exception:
        pass
    import psycopg
    with psycopg.connect(os.environ["DATABASE_URL"]) as c, c.cursor() as cur:
        cur.execute(
            "select oaid,title,publication_year,counts_by_year from works "
            "where primary_subfield=%s and publication_year between %s and %s "
            "and counts_by_year is not null and title is not null "
            "and mod(abs(hashtext(oaid)), 100) < %s",
            (SUBFIELD, YEARS[0], YEARS[1], SAMPLE_PCT),
        )
        return [[o, t, p, cb] for o, t, p, cb in cur.fetchall()]


def _cumtraj(pub, cby):
    d = {}
    if isinstance(cby, dict):
        d = {int(k): int(v) for k, v in cby.items()}
    else:
        for e in cby or []:
            if isinstance(e, dict):
                y = e.get("year"); n = e.get("cited_by_count", e.get("count"))
                if y is not None and n is not None:
                    d[int(y)] = int(n)
    run, out = 0, []
    for a in AGES:
        run += d.get(pub + a, 0); out.append(run)
    return out


def _bucket(x):
    for b in range(len(FAN_EDGES) - 1):
        if FAN_EDGES[b] <= x < FAN_EDGES[b + 1]:
            return b
    return len(FAN_EDGES) - 2


def compute(rows):
    papers = [{"oaid": o, "title": t, "pub": p, "tr": _cumtraj(p, cb)} for o, t, p, cb in rows]
    N = len(papers)
    M = np.array([p["tr"] for p in papers], float)
    bands = {p: [round(float(np.percentile(M[:, i], p)), 1) for i in range(10)] for p in BAND_PS}

    pcts = np.zeros((N, 10))
    for i in range(10):
        s = np.sort(M[:, i])
        pcts[:, i] = 100.0 * (np.searchsorted(s, M[:, i], "left") + np.searchsorted(s, M[:, i], "right")) / 2 / N
    for k, p in enumerate(papers):
        p["pct"] = [round(float(pcts[k, i]), 1) for i in range(10)]
    ev, e2 = pcts[:, -1], pcts[:, 1]

    star = max(range(N), key=lambda i: (ev[i] >= 99) * e2[i] + ev[i] / 1000)
    sleeper = max(range(N), key=lambda i: (ev[i] - e2[i]) + (ev[i] >= 90) * 20 - (e2[i] > 70) * 50)
    solid = min(range(N), key=lambda i: abs(ev[i] - 80) + abs(e2[i] - 70) * 0.3)
    typical = min(range(N), key=lambda i: abs(ev[i] - 55) + M[i][-1] * 0.05)
    fc = [i for i in range(N) if e2[i] >= 88 and ev[i] <= e2[i] - 8]
    flash = max(fc, key=lambda i: e2[i] - ev[i]) if fc else None
    sel = {"star": star, "sleeper": sleeper, "solid": solid, "typical": typical}
    if flash is not None:
        sel["flash"] = flash

    fan = {}
    for i in range(10):
        bk = np.array([_bucket(v) for v in M[:, i]])
        for b in set(bk.tolist()):
            evb = pcts[bk == b, -1]
            if len(evb) >= 8:
                fan[(i, b)] = [round(float(np.percentile(evb, q)), 1) for q in (5, 50, 95)]

    def fan_for(i):
        return [fan.get((a, _bucket(M[i, a])), [round(float(pcts[i, a]), 1)] * 3) for a in range(10)]

    arch = {}
    for name, i in sel.items():
        p = papers[i]
        arch[name] = {"title": p["title"][:95], "oaid": p["oaid"], "pub": p["pub"],
                      "citations": [int(x) for x in p["tr"]], "pct": p["pct"],
                      "ev": int(p["tr"][-1]), "fan": fan_for(i)}
    return {
        "ages": AGES, "N": N,
        "cohort": "Management Science & Operations Research (OpenAlex subfield 1803), 2011–2014, pooled by paper age",
        "band_ps": BAND_PS, "bands": bands, "archetypes": arch,
        "uncited_frac": round(float(np.mean(M[:, -1] == 0)), 3),
        "median_ev": float(np.median(M[:, -1])), "p99_age10": bands[99][-1],
    }


def render(data):
    tmpl = open(TEMPLATE).read()
    page = tmpl.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    assert "__DATA__" not in page, "template placeholder not replaced"
    open(OUT_PAGE, "w").write(page)
    print(f"wrote {os.path.relpath(OUT_PAGE, ROOT)}  (N={data['N']}, uncited@10={data['uncited_frac']:.1%})")


if __name__ == "__main__":
    if "--no-pull" in sys.argv:
        data = json.load(open(DATA_JSON))
    else:
        data = compute(pull())
        json.dump(data, open(DATA_JSON, "w"), indent=1)
        print(f"pulled + computed -> {os.path.relpath(DATA_JSON, ROOT)}")
    render(data)
