#!/usr/bin/env python3
"""Seed the datastore from the UI mock data (docs/mocks/*.js) so the web app
works end-to-end for the POC, before the real pipeline has run.

Writes: works, qal_records (illustrative QaL), authors, author_works.
Everything written here is the POC stand-in and is labelled
"illustrative pending calibration" in the UI (QaL_spec.md §10).

Usage:  DATABASE_URL=... python pipeline/seed_demo.py
"""
import json
import math
import os
import re
import html
from pathlib import Path

import psycopg

NOW = 2026
ROOT = Path(__file__).resolve().parents[1]
MOCKS = ROOT / "docs" / "mocks"


def load_window_json(path: Path):
    """Parse a `window.NAME = <json>;` mock file into a Python object."""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"window\.\w+\s*=\s*(.*);\s*$", text, re.S)
    if not m:
        raise ValueError(f"could not parse {path}")
    return json.loads(m.group(1))


def clean(s):
    if s is None:
        return None
    return html.unescape(s)


def illustrative_qal(obs, year):
    if obs is None:
        return None
    pt = round(obs)
    age = max(1, NOW - (year or NOW) + 1)
    hw = min(19, max(3, round((1 - min(age, 10) / 10) * 16 + 3)))
    return {"point": pt, "lo": max(0, pt - hw), "hi": min(100, pt + max(1, round(hw / 3)))}


def _erf(x):
    t = 1 / (1 + 0.3275911 * abs(x))
    y = 1 - ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t
             + 0.254829592) * t * math.exp(-x * x)
    return y if x >= 0 else -y


def _norm_cdf(x, mean, sd):
    if sd <= 0:
        return 1.0 if x >= mean else 0.0
    return 0.5 * (1 + _erf((x - mean) / (sd * math.sqrt(2))))


def class_prob(q):
    sd = max(1.5, (q["hi"] - q["lo"]) / 3.2897)
    ge = lambda k: round((1 - _norm_cdf(k, q["point"], sd)) * 100) / 100
    return {"ge50": ge(50), "ge75": ge(75), "ge90": ge(90), "ge95": ge(95), "ge99": ge(99)}


def upsert_work(cur, w):
    raw = {"authors": clean(w.get("authors")), "venue": clean(w.get("venue")),
           "subfield_label": clean(w.get("subfield"))}
    cur.execute(
        """
        insert into works (oaid, doi, title, publication_year, primary_subfield,
                           primary_field, cited_by_count, is_oa, is_retracted, raw)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        on conflict (oaid) do update set
          doi=excluded.doi, title=excluded.title, publication_year=excluded.publication_year,
          primary_subfield=excluded.primary_subfield, primary_field=excluded.primary_field,
          cited_by_count=excluded.cited_by_count, is_oa=excluded.is_oa,
          is_retracted=excluded.is_retracted, raw=excluded.raw
        """,
        (w["oaid"], w.get("doi"), clean(w.get("title")), w.get("year"), w.get("sid"),
         clean(w.get("field")), w.get("cites") or 0, bool(w.get("oa")),
         bool(w.get("retracted")), json.dumps(raw)),
    )


def upsert_qal(cur, w):
    obs = w.get("obs")
    calibrated = bool(w.get("calibrated"))
    q = illustrative_qal(obs, w.get("year")) if calibrated else None
    ref = {"field": f"subfields/{w['sid']}" if w.get("sid") else None,
           "field_label": clean(w.get("subfield")), "vintage_year": w.get("year"),
           "n": w.get("n")}
    cur.execute(
        """
        insert into qal_records (oaid, reference_class, obs_percentile, calibrated,
                                 qal_point, qal_ci_lo, qal_ci_hi, class_prob,
                                 method_version, data_snapshot)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        on conflict (oaid) do update set
          reference_class=excluded.reference_class, obs_percentile=excluded.obs_percentile,
          calibrated=excluded.calibrated, qal_point=excluded.qal_point,
          qal_ci_lo=excluded.qal_ci_lo, qal_ci_hi=excluded.qal_ci_hi,
          class_prob=excluded.class_prob, method_version=excluded.method_version,
          data_snapshot=excluded.data_snapshot
        """,
        (w["oaid"], json.dumps(ref), obs, calibrated,
         q["point"] if q else None, q["lo"] if q else None, q["hi"] if q else None,
         json.dumps(class_prob(q)) if q else None, "qal-0.1", "mock-demo-2026-06"),
    )


def main():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL not set")

    explore = load_window_json(MOCKS / "exploreData.js")
    author = load_window_json(MOCKS / "authorData.js")

    n_works = 0
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            # explore records
            for w in explore:
                upsert_work(cur, w)
                upsert_qal(cur, w)
                n_works += 1

            # author + their works
            a = author["author"]
            cur.execute(
                """
                insert into authors (oaid, orcid, display_name, affiliation,
                                     works_count, cited_by_count, seed)
                values (%s,%s,%s,%s,%s,%s,%s)
                on conflict (oaid) do update set
                  orcid=excluded.orcid, display_name=excluded.display_name,
                  affiliation=excluded.affiliation, works_count=excluded.works_count,
                  cited_by_count=excluded.cited_by_count, seed=excluded.seed
                """,
                (a["oaid"], a.get("orcid"), clean(a["name"]), clean(a.get("aff")),
                 a.get("works_count"), a.get("cites"), a.get("seed")),
            )
            for w in author["works"]:
                upsert_work(cur, w)
                upsert_qal(cur, w)
                n_works += 1
                cur.execute(
                    """insert into author_works (author_oaid, work_oaid) values (%s,%s)
                       on conflict do nothing""",
                    (a["oaid"], w["oaid"]),
                )
        conn.commit()

    print(f"seeded {n_works} work rows (+ qal), 1 author, "
          f"{len(author['works'])} author links")


if __name__ == "__main__":
    main()
