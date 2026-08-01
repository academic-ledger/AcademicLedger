"""In-region dump of eventual-citation histograms per (field, subfield, vintage) for the four QaL
target fields — feeds the gaming-robustness exhibit (Exhibit E). Reads the OpenAlex snapshot with
DuckDB, samples up to PER papers per cohort, computes eventual cumulative citations at age H from
counts_by_year, keeps the top-2 subfields per field (by sampled size) over vintages 2011-2013, and
prints a gzip+base64 JSON blob {"fid|sid|yr": {cites: freq}} to the serial console in <=2000-char
chunks (reassembled by the launcher). No Neon write. Same estimator convention as calib_lib.cum_at_age.

Env: FACTORY_FILE_LIMIT (0=all part files), COH_PER (sample per cohort, default 12000).
"""
import os, sys, json, gzip, base64, urllib.request
from collections import Counter, defaultdict

FIELDS = {"13": "Biochem", "18": "DecSci", "20": "Econ-Fin", "12": "Arts-Hum"}
VMIN, VMAX = 2011, 2013; H = 10; MINN = 800
PER = int(os.environ.get("COH_PER", "12000"))
MANIFEST = "https://openalex.s3.amazonaws.com/data/jsonl/works/manifest.json"
S3, HTTPS = "s3://openalex/", "https://openalex.s3.amazonaws.com/"


def part_urls(limit):
    m = json.load(urllib.request.urlopen(MANIFEST)); e = m["files"]
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
      ), s AS (SELECT *, row_number() OVER (PARTITION BY fid,sid,yr ORDER BY random()) AS rn FROM f)
      SELECT fid, sid, yr, cby FROM s WHERE rn <= {PER}
    """
    return con.execute(q).fetchall()


def cum_at_age(cby, pub_year, age):
    return sum(int(v) for y, v in cby.items() if int(y) <= pub_year + age)


def main():
    limit = int(os.environ.get("FACTORY_FILE_LIMIT", "0"))
    urls = part_urls(limit)
    print(f"FACTORY-COH scanning {len(urls)} part files (PER={PER})", flush=True)
    rows = scan(urls)
    print(f"FACTORY-COH sampled rows: {len(rows)}", flush=True)
    hist = defaultdict(Counter)
    subtot = defaultdict(Counter)   # fid -> {sid: total sampled}
    for fid, sid, yr, cby in rows:
        if fid not in FIELDS:
            continue
        try:
            d = {int(e["year"]): int(e["cited_by_count"]) for e in json.loads(cby)}
        except Exception:
            continue
        ev = cum_at_age(d, int(yr), H)
        hist[f"{fid}|{sid}|{yr}"][ev] += 1
        subtot[fid][sid] += 1
    # keep the top-2 subfields per field (by sampled size), cohorts with >= MINN papers
    keep_sids = {fid: {s for s, _ in c.most_common(2)} for fid, c in subtot.items()}
    out = {}
    for k, v in hist.items():
        fid, sid, yr = k.split("|")
        if sid in keep_sids.get(fid, set()) and sum(v.values()) >= MINN:
            out[k] = dict(v)
    print(f"FACTORY-COH cohorts kept: {len(out)} across fields "
          f"{ {f: sorted(keep_sids.get(f, [])) for f in FIELDS} }", flush=True)
    blob = base64.b64encode(gzip.compress(json.dumps(out, separators=(',', ':')).encode())).decode()
    CH = 500   # keep lines well under the serial-console ~1KB line-truncation limit
    n = (len(blob) + CH - 1) // CH
    lines = [f"FACTORY-COH DATA {i:03d} {len(blob[i*CH:(i+1)*CH])} {blob[i*CH:(i+1)*CH]}" for i in range(n)]
    # write chunks to a file; the launcher's user-data re-emits them repeatedly so the periodically-
    # updated (and laggy) console API captures a complete set across snapshots before shutdown.
    with open("/tmp/cohorts_out.txt", "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"FACTORY-COH BYTES {len(blob)} chunks {n}", flush=True)
    print("FACTORY-COH DONE", flush=True)


if __name__ == "__main__":
    main()
