"""In-region OpenAlex factory: build cohort_percentiles for EVERY (subfield, year).

Replaces the API-limited pull_cohort.py -> build_percentiles.py path for the universal
layer. Scans the full OpenAlex works snapshot (public S3, gzipped JSON Lines) with DuckDB,
computes the same mid-rank empirical CDF per (subfield, year) as build_percentiles.py, and
upserts cohort_percentiles + subfields into Neon. Designed to run on a throwaway in-region
EC2 box (~1h for the full 492M-work corpus); see academic-ledger-aws-factory memory.

Env:
  DATABASE_URL        Neon connection string (required to write; dry-run prints if absent)
  OPENALEX_SNAPSHOT   snapshot label, e.g. 'openalex-2026-06' (default 'openalex-dev')
  MIN_COHORT_N        skip cohorts thinner than this (default 50, matches build_percentiles)
  FACTORY_FILE_LIMIT  read only the first N part files (0 = all; use small N to smoke-test)
  DUCKDB_THREADS      override DuckDB thread count (default: all cores)
  DUCKDB_HOME         home dir for DuckDB extensions (default /tmp; needed when run as root)
"""
import os, sys, json, time, urllib.request

# Local runs load DATABASE_URL etc. from the repo .env (pipeline/ is on sys.path[0] when run as
# `python pipeline/factory.py`). On the EC2 box this file is copied alone, so the import fails and
# we fall through to plain env vars exported by the launcher. Either way: no secret is printed.
try:
    import _env; _env.load_env()
except Exception:
    pass

MANIFEST = "https://openalex.s3.amazonaws.com/data/works/manifest"
S3_PREFIX = "s3://openalex/"
HTTPS_PREFIX = "https://openalex.s3.amazonaws.com/"


def part_urls(limit=0):
    m = json.load(urllib.request.urlopen(MANIFEST))
    entries = m["entries"]
    total = sum(e["meta"]["record_count"] for e in entries)
    if limit and limit > 0:
        entries = entries[:limit]
    urls = [e["url"].replace(S3_PREFIX, HTTPS_PREFIX) for e in entries]
    return urls, total, len(entries)


def scan(urls):
    """One snapshot pass -> (cohort breakpoint rows, subfield name rows). All heavy work in DuckDB."""
    import duckdb
    con = duckdb.connect()
    con.execute("SET home_directory=%s;" % repr(os.environ.get("DUCKDB_HOME", "/tmp")))
    con.execute("SET temp_directory=%s;" % repr(os.environ.get("DUCKDB_TMP", "/tmp/duckdb_spill")))
    threads = os.environ.get("DUCKDB_THREADS")
    if threads:
        con.execute("SET threads=%d;" % int(threads))
    con.execute("INSTALL httpfs; LOAD httpfs;")

    cols = ("{'id':'VARCHAR','publication_year':'INTEGER',"
            "'cited_by_count':'INTEGER','primary_topic':'JSON'}")
    src = ("read_json(%s, compression='gzip', columns=%s, ignore_errors=true)"
           % (urls, cols))

    # ONE streaming aggregation -> one row per (subfield, year, cites). DuckDB hash-aggregates the
    # ~470M input works on the fly and NEVER materializes them (that would be ~24GB); the result `g`
    # is only ~millions of small group rows. Subfield id = trailing integer of the OpenAlex subfield
    # URL (.../subfields/1803 -> '1803'), matching works.primary_subfield. The display name is
    # functionally dependent on sid, so any_value carries it for free (no second corpus scan).
    con.execute(f"""
        CREATE TEMP TABLE g AS
        SELECT regexp_extract(json_extract_string(primary_topic,'$.subfield.id'), '(\\d+)$', 1) AS sid,
               any_value(json_extract_string(primary_topic,'$.subfield.display_name'))           AS sname,
               publication_year AS yr,
               cited_by_count   AS cites,
               count(*)         AS c
        FROM {src}
        WHERE primary_topic IS NOT NULL
          AND json_extract_string(primary_topic,'$.subfield.id') IS NOT NULL
          AND publication_year IS NOT NULL
          AND cited_by_count IS NOT NULL
        GROUP BY 1, 3, 4
    """)

    min_n = int(os.environ.get("MIN_COHORT_N", "50"))
    # Mid-rank percentile per distinct cite count (identical math to build_percentiles.cdf_breakpoints):
    # pct = 100*(below + equal/2)/n, where below = cohort count strictly below this cite value.
    cdf_rows = con.execute(f"""
        WITH w AS (
            SELECT sid, yr, cites, c,
                   COALESCE(sum(c) OVER (PARTITION BY sid,yr ORDER BY cites
                            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS below,
                   sum(c) OVER (PARTITION BY sid,yr) AS n
            FROM g
        )
        SELECT sid, yr, n, cites, round(100.0*(below + c/2.0)/n, 3) AS pct
        FROM w WHERE n >= {min_n}
        ORDER BY sid, yr, cites
    """).fetchall()

    sf_rows = con.execute("""
        SELECT sid, any_value(sname) FROM g
        WHERE sid IS NOT NULL AND sname IS NOT NULL GROUP BY sid
    """).fetchall()
    nworks = con.execute("SELECT sum(c) FROM g").fetchone()[0]
    return cdf_rows, sf_rows, nworks


def write_neon(cdf_rows, sf_rows, snapshot):
    import psycopg
    db = os.environ["DATABASE_URL"]
    # Group flat breakpoint rows -> one CDF array per (subfield, year).
    cohorts = {}
    for sid, yr, n, cites, pct in cdf_rows:
        key = (sid, yr, n)
        cohorts.setdefault(key, []).append({"cites": int(cites), "pct": float(pct)})

    conn = psycopg.connect(db)
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO subfields (id,name) VALUES (%s,%s) "
            "ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name",
            [(sid, name) for sid, name in sf_rows])
        cur.executemany(
            "INSERT INTO cohort_percentiles (subfield,publication_year,n,cdf,snapshot) "
            "VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (subfield,publication_year,snapshot) "
            "DO UPDATE SET n=EXCLUDED.n, cdf=EXCLUDED.cdf",
            [(sid, yr, n, json.dumps(cdf), snapshot) for (sid, yr, n), cdf in cohorts.items()])
    conn.commit(); conn.close()
    return len(cohorts), len(sf_rows)


def main():
    t0 = time.time()
    limit = int(os.environ.get("FACTORY_FILE_LIMIT", "0"))
    snapshot = os.environ.get("OPENALEX_SNAPSHOT", "openalex-dev")
    urls, total, nfiles = part_urls(limit)
    print(f"FACTORY start: {nfiles} part files (corpus total {total} works), snapshot='{snapshot}'", flush=True)

    cdf_rows, sf_rows, nworks = scan(urls)
    print(f"FACTORY scanned {nworks} works in {time.time()-t0:.0f}s -> "
          f"{len({(r[0],r[1]) for r in cdf_rows})} cohorts, {len(sf_rows)} subfields", flush=True)

    if not os.environ.get("DATABASE_URL"):
        print("FACTORY dry-run (no DATABASE_URL): not writing.", flush=True)
        return
    ncoh, nsf = write_neon(cdf_rows, sf_rows, snapshot)
    print(f"FACTORY wrote {ncoh} cohorts + {nsf} subfields to Neon in {time.time()-t0:.0f}s total", flush=True)
    # Independent read-back confirmation (the only way to verify from outside this network).
    import psycopg
    with psycopg.connect(os.environ["DATABASE_URL"]) as c:
        got = c.execute("SELECT count(*) FROM cohort_percentiles WHERE snapshot=%s", (snapshot,)).fetchone()[0]
        allsnaps = c.execute("SELECT snapshot, count(*) FROM cohort_percentiles GROUP BY snapshot ORDER BY snapshot DESC").fetchall()
    print(f"FACTORY readback: {got} cohort_percentiles rows live in Neon for snapshot='{snapshot}'", flush=True)
    # The serving layer picks MAX(snapshot) per cohort; this shows whether our label wins.
    print("FACTORY all snapshots (desc; serving uses the top one per cohort): "
          + " | ".join(f"{s}={n}" for s, n in allsnaps), flush=True)


if __name__ == "__main__":
    main()
