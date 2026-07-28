#!/usr/bin/env python3
"""Build rxiv_cohort_merged.json: per-article early downloads (Rxivist) + eventual citations (OpenAlex).

Step 1 of the download-to-citation pilot (analyze.py is step 2). Reads the open Rxivist database dump
to get per-article monthly PDF downloads, cumulates the first 1/3/6/12 months from posting for the
medRxiv-2019 and bioRxiv-2017 cohorts, then joins eventual citations from OpenAlex by DOI.

Prereqs:
  - Download the Rxivist dump (Postgres custom-format, ~493 MiB) from Zenodo 10.5281/zenodo.7688682:
      curl -sL -o rxivist.backup "https://zenodo.org/records/7688682/files/rxivist.backup?download=1"
  - pip install pgdumplib          # pure-python reader for -Fc dumps (no Postgres server needed)
Run:
  ../../.venv/bin/python extract_downloads.py /path/to/rxivist.backup
"""
import os, sys, json, time, urllib.parse, urllib.request
import pgdumplib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "rxiv_cohort_merged.json")
MAILTO = os.environ.get("OPENALEX_MAILTO", "ktulrich@gmail.com")
BIO_SAMPLE_MOD = 22   # deterministic ~22% sample of bioRxiv 2017 for the citation join


def extract(dump_path):
    dump = pgdumplib.load(dump_path)
    # prod.articles cols: 0 id, 4 doi, 5 collection, 9 posted, 11 repo
    sel = {}
    for row in dump.table_data("prod", "articles"):
        rid, doi, posted, repo = row[0], row[4], row[9], row[11]
        if not posted or not doi:
            continue
        yr = str(posted)[:4]
        if repo == "medrxiv" and yr == "2019":
            sel[rid] = {"repo": "medrxiv", "doi": doi, "posted": str(posted)[:7], "coll": row[5]}
        elif repo == "biorxiv" and yr == "2017":
            sel[rid] = {"repo": "biorxiv", "doi": doi, "posted": str(posted)[:7], "coll": row[5]}
    # prod.article_traffic cols: 0 id, 1 article, 2 month, 3 year, 4 abstract, 5 pdf
    traf = {}
    for row in dump.table_data("prod", "article_traffic"):
        aid = row[1]
        if aid in sel:
            try:
                traf.setdefault(aid, []).append((int(row[3]), int(row[2]), int(row[5] or 0)))
            except (TypeError, ValueError):
                pass

    def early(posted, rows, n):
        py, pm = int(posted[:4]), int(posted[5:7])
        return sum(pdf for (ty, tm, pdf) in rows if (ty - py) * 12 + (tm - pm) + 1 <= n)

    out = []
    for rid, meta in sel.items():
        rows = traf.get(rid, [])
        if not rows:
            continue
        out.append({**meta,
                    "dl1": early(meta["posted"], rows, 1), "dl3": early(meta["posted"], rows, 3),
                    "dl6": early(meta["posted"], rows, 6), "dl12": early(meta["posted"], rows, 12),
                    "dl_total": sum(r[2] for r in rows)})
    return out


def join_citations(cohort):
    sel = [x for x in cohort if x["repo"] == "medrxiv" or (hash(x["doi"]) % 100) < BIO_SAMPLE_MOD]

    def api(url):
        for _ in range(3):
            try:
                return json.load(urllib.request.urlopen(
                    urllib.request.Request(url, headers={"User-Agent": f"aL-research (mailto:{MAILTO})"}), timeout=40))
            except Exception:
                time.sleep(1)
        return {"results": []}

    norm = lambda d: (d or "").lower().replace("https://doi.org/", "")
    cit = {}
    dois = [x["doi"] for x in sel]
    for i in range(0, len(dois), 50):
        f = "doi:" + "|".join(dois[i:i + 50])
        url = ("https://api.openalex.org/works?filter=" + urllib.parse.quote(f) +
               "&select=doi,cited_by_count,counts_by_year,publication_year&per-page=50&mailto=" + MAILTO)
        for r in api(url).get("results", []):
            cit[norm(r.get("doi"))] = {"c": r.get("cited_by_count", 0), "cby": r.get("counts_by_year", [])}
    merged = []
    for x in sel:
        r = cit.get(norm(x["doi"]))
        if not r:
            continue
        py = int(x["posted"][:4])
        c5 = sum(e["cited_by_count"] for e in (r["cby"] or []) if e["year"] <= py + 5)
        merged.append({**x, "cites": r["c"], "cites5": c5})
    return merged


def add_published_citations(merged):
    """Robustness: use citations of the *published version of record*, not just the preprint DOI.

    Many preprints are later published; OpenAlex attributes most citations to the journal version, so
    the preprint-DOI count undercounts. We map each preprint to its published DOI via the bioRxiv/
    medRxiv API `published` field, fetch that version's citations, and set cites_best = max(preprint,
    published). Adds `published` (0/1) and `cites_best` to each record.
    """
    def get(url):
        for _ in range(4):
            try:
                return json.load(urllib.request.urlopen(
                    urllib.request.Request(url, headers={"User-Agent": "aL-research"}), timeout=45))
            except Exception:
                time.sleep(1.5)
        return {}

    def pubmap(server, start, end):
        m, cur = {}, 0
        while True:
            d = get(f"https://api.biorxiv.org/details/{server}/{start}/{end}/{cur}/json")
            coll = d.get("collection", [])
            if not coll:
                break
            for it in coll:
                p = (it.get("published") or "").strip()
                m[it["doi"].lower()] = p if p and p.upper() != "NA" else None
            total = int(d["messages"][0]["total"]); cur += len(coll)
            if cur >= total:
                break
            time.sleep(0.03)
        return m

    pm = {**pubmap("medrxiv", "2019-01-01", "2019-12-31"),
          **pubmap("biorxiv", "2017-01-01", "2017-12-31")}
    norm = lambda d: (d or "").lower().replace("https://doi.org/", "")
    pdois = sorted({pm[x["doi"].lower()] for x in merged if pm.get(x["doi"].lower())})
    pcit = {}
    for i in range(0, len(pdois), 50):
        f = "doi:" + "|".join(pdois[i:i + 50])
        url = ("https://api.openalex.org/works?filter=" + urllib.parse.quote(f) +
               "&select=doi,cited_by_count&per-page=50&mailto=" + MAILTO)
        for r in get(url).get("results", []):
            pcit[norm(r.get("doi"))] = r.get("cited_by_count", 0)
    for x in merged:
        pd = pm.get(x["doi"].lower()); pc = pcit.get(norm(pd)) if pd else None
        x["published"] = 1 if pd else 0
        x["cites_best"] = max(x["cites"], pc or 0)
    return merged


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: extract_downloads.py /path/to/rxivist.backup")
    cohort = extract(sys.argv[1])
    print(f"extracted downloads for {len(cohort)} papers; joining OpenAlex citations…")
    merged = join_citations(cohort)
    print("adding published-version citations (robustness)…")
    merged = add_published_citations(merged)
    json.dump(merged, open(OUT, "w"))
    print(f"wrote {os.path.relpath(OUT, HERE)}  ({len(merged)} papers; preprint + published citations)")
