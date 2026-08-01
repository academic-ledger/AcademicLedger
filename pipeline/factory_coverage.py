"""In-region cross-field calibration COVERAGE — QaL paper Exhibit C, full power.

Reads the OpenAlex works snapshot with DuckDB, samples up to COV_PER papers per (subfield, vintage)
cohort for the four target fields, and runs the EXACT shipped conformal leave-one-vintage-out coverage
back-test (calib_lib, same method as pipeline/backtest.py) per field. Prints per-field coverage to
stdout (read over the serial console). No Neon write. Runs on the throwaway EC2 box next to the S3
snapshot; calib_lib.py is embedded alongside by the launcher.

Env: FACTORY_FILE_LIMIT (0=all part files), COV_PER (sample per cohort, default 8000).
"""
import os, sys, json, urllib.request
import numpy as np
sys.path.insert(0, "/tmp"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calib_lib as cl

FIELDS = {"13": "Biochemistry-MolBio", "18": "Decision-Sciences",
          "20": "Economics-Finance", "12": "Arts-Humanities"}
VMIN, VMAX = 2008, 2015; H = 10; MINN = 200
PER = int(os.environ.get("COV_PER", "8000"))
MANIFEST = "https://openalex.s3.amazonaws.com/data/jsonl/works/manifest.json"
S3, HTTPS = "s3://openalex/", "https://openalex.s3.amazonaws.com/"


def part_urls(limit):
    m = json.load(urllib.request.urlopen(MANIFEST)); e = m["files"]  # snapshot reorg 2026: data/jsonl/works, key 'files'
    if limit and limit > 0:
        e = e[:limit]
    return [x["url"].replace(S3, HTTPS) for x in e]


def scan(urls):
    import duckdb
    con = duckdb.connect()
    con.execute("SET home_directory=%s;" % repr(os.environ.get("DUCKDB_HOME", "/tmp")))
    con.execute("SET temp_directory=%s;" % repr(os.environ.get("DUCKDB_TMP", "/tmp/dd")))
    con.execute("INSTALL httpfs; LOAD httpfs;")
    cols = "{'id':'VARCHAR','publication_year':'INTEGER','primary_topic':'JSON','counts_by_year':'JSON'}"
    src = "read_json(%s, compression='gzip', columns=%s, ignore_errors=true)" % (urls, cols)
    q = f"""
      WITH f AS (
        SELECT regexp_extract(json_extract_string(primary_topic,'$.field.id'),'(\\d+)$',1) AS fid,
               regexp_extract(json_extract_string(primary_topic,'$.subfield.id'),'(\\d+)$',1) AS sid,
               publication_year AS yr, CAST(counts_by_year AS VARCHAR) AS cby
        FROM {src}
        WHERE primary_topic IS NOT NULL AND counts_by_year IS NOT NULL AND publication_year IS NOT NULL
          AND publication_year BETWEEN {VMIN} AND {VMAX}
          AND regexp_extract(json_extract_string(primary_topic,'$.field.id'),'(\\d+)$',1) IN ('12','13','18','20')
      ), s AS (SELECT *, row_number() OVER (PARTITION BY sid,yr ORDER BY random()) AS rn FROM f)
      SELECT fid, sid, yr, cby FROM s WHERE rn <= {PER}
    """
    return con.execute(q).fetchall()


def conformal_from_train(prepared, train_vintages, H):
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
            sc = np.asarray(sc); n = len(sc); lvl = min(1.0, np.ceil((n + 1) * 0.90) / n)
            Q[a] = float(np.quantile(sc, lvl, method="higher"))
        else:
            Q[a] = 0.0
    return Q


def main():
    limit = int(os.environ.get("FACTORY_FILE_LIMIT", "0"))
    urls = part_urls(limit)
    print(f"FACTORY-COV scanning {len(urls)} part files (PER={PER})", flush=True)
    rows = scan(urls)
    print(f"FACTORY-COV sampled rows: {len(rows)}", flush=True)
    perfield = {}
    for fid, sid, yr, cby in rows:
        try:
            d = {int(e["year"]): int(e["cited_by_count"]) for e in json.loads(cby)}
        except Exception:
            continue
        perfield.setdefault(fid, {}).setdefault(sid, {}).setdefault(int(yr), []).append(d)
    for fid, name in FIELDS.items():
        prepared_by_comm = {}
        for sid, vmap in perfield.get(fid, {}).items():
            pv = {v: cl.prepare(lst, v, H) for v, lst in vmap.items() if len(lst) >= MINN}
            if len(pv) >= 3:
                prepared_by_comm[sid] = pv
        overall = [0, 0]; byage = {a: [0, 0] for a in range(1, H)}
        for sid, prepared in prepared_by_comm.items():
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
                        if cell is None:
                            continue
                        lo, hi = cl.predict_interval(cell, Q.get(a, 0.0))
                        hit = 1 if lo <= y <= hi else 0
                        overall[0] += hit; overall[1] += 1; byage[a][0] += hit; byage[a][1] += 1
        cov = overall[0] / overall[1] if overall[1] else float("nan")
        ba = {a: round(byage[a][0] / byage[a][1], 3) for a in range(1, H) if byage[a][1]}
        print(f"FACTORY-COV RESULT {name} coverage={cov:.4f} n={overall[1]} "
              f"subfields={len(prepared_by_comm)} by_age={ba}", flush=True)
    print("FACTORY-COV DONE", flush=True)


if __name__ == "__main__":
    main()
